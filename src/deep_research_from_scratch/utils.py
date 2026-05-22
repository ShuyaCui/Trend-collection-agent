
"""Research Utilities and Tools.

This module provides search and content processing utilities for the research agent,
including web search capabilities and content summarization tools.
"""

import base64
import contextvars
import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import requests
import urllib3
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.tools import InjectedToolArg, tool
from requests.exceptions import SSLError
from tavily import TavilyClient
from typing_extensions import Annotated, List, Literal

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.prompts import summarize_webpage_prompt
from deep_research_from_scratch.state_research import ImageResult, Summary

load_dotenv()
logger = logging.getLogger(__name__)

# ===== SSL CONFIGURATION =====
# Set DISABLE_SSL_VERIFY=true in .env to skip certificate verification when
# operating behind a corporate proxy with self-signed certificates.
_DISABLE_SSL = os.getenv("DISABLE_SSL_VERIFY", "").lower() in ("1", "true", "yes")
if _DISABLE_SSL:
    import ssl

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Patch Python's ssl module so stdlib HTTPS clients (urllib.request,
    # http.client) also skip verification.
    ssl._create_default_https_context = ssl._create_unverified_context  # noqa: SLF001

    # Remove env vars that would re-enable cert verification inside
    # requests.Session.merge_environment_settings.
    for _env_var in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        os.environ.pop(_env_var, None)

    # Patch requests.Session.merge_environment_settings to force verify=False.
    # Why this level:
    #   requests.post() → Session() → session.request() →
    #   merge_environment_settings() → session.send(verify=...)
    # Thread-safe: each call operates on its own settings dict —
    #   no shared mutable state, so concurrent asyncio.gather() sub-agents
    #   cannot race each other (unlike the old requests.post swap approach).
    # Autoreload-safe: requests is in site-packages, so %autoreload 2
    #   does not reload it and the class-level patch persists.
    if not getattr(requests.Session, "_ssl_patched", False):
        _orig_merge = requests.Session.merge_environment_settings

        def _merge_no_verify(  # noqa: ANN001
            self, url, proxies=None, stream=False, verify=True, cert=None,
            *, _orig=_orig_merge,
        ):
            if proxies is None:
                proxies = {}
            settings = _orig(self, url, proxies, stream, verify, cert)
            settings["verify"] = False
            return settings

        requests.Session.merge_environment_settings = _merge_no_verify
        requests.Session._ssl_patched = True  # type: ignore[attr-defined]

# ===== UTILITY FUNCTIONS =====

def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")

def get_current_dir() -> Path:
    """Get the current directory of the module.

    This function is compatible with Jupyter notebooks and regular Python scripts.

    Returns:
        Path object representing the current directory
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:  # __file__ is not defined
        return Path.cwd()

# ===== CONFIGURATION =====

# Derive summarization model from AZURE_OPENAI_DEPLOYMENT when no explicit
# override is set. This ensures the deployment name is always valid.
_env_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
_DEFAULT_SUMMARIZATION_MODEL = (
    f"azure_openai:{_env_deployment}" if _env_deployment else "azure_openai:GPT-41-2025-04-14"
)
_runtime_config: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "runtime_config",
    default={},
)


def set_runtime_config(configurable: dict | None) -> None:
    """Store runtime model overrides for tool-side model resolution."""
    _runtime_config.set(dict(configurable or {}))


def get_runtime_config() -> dict:
    """Return the current runtime model overrides for tool-side helpers."""
    return dict(_runtime_config.get())


_last_search_images: list[ImageResult] = []


def get_last_search_images() -> list[ImageResult]:
    """Retrieve images extracted from the most recent search call.

    Used by tool_node to pass image metadata into the agent state
    without changing the tool's string return interface.
    """
    return list(_last_search_images)




def normalize_model_id(model_id: str) -> str:
    """Normalize Azure model identifiers to use the expected deployment casing."""
    provider, separator, deployment = model_id.partition(":")
    if not separator:
        return model_id
    return f"{provider}{separator}{deployment.upper()}"


def _build_summarization_model(
    model_id: str | None = None,
    temperature: float = 0.0,
):
    """Build the summarization model with a fresh GenAI token.

    Fallback order is:
    1. Explicit ``model_id`` argument
    2. Runtime ``summarization_model`` override
    3. Runtime ``research_model`` override
    4. ``AZURE_OPENAI_DEPLOYMENT`` env var (same as main research model)
    5. Hardcoded default (GPT-41-2025-04-14)
    """
    runtime_config = get_runtime_config()
    resolved_model_id = (
        model_id
        or runtime_config.get("summarization_model")
        or runtime_config.get("research_model")
        or _DEFAULT_SUMMARIZATION_MODEL
    )
    normalized_model_id = normalize_model_id(resolved_model_id)
    deployment = normalized_model_id.split(":")[-1]
    return init_chat_model(
        model=normalized_model_id,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=deployment,
        api_key=GenAIToken().token(),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        default_headers={
            "project-name": os.getenv("HEADERS_PROJECT_NAME"),
            "userid": os.getenv("HEADERS_USERID"),
        },
        temperature=temperature,
    )


tavily_client = TavilyClient()


def _enable_insecure_requests_session() -> None:
    """Force requests-backed HTTPS calls to skip certificate verification."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if getattr(requests.Session, "_ssl_patched", False):
        return

    _orig_merge = requests.Session.merge_environment_settings

    def _merge_no_verify(  # noqa: ANN001
        self, url, proxies=None, stream=False, verify=True, cert=None,
        *, _orig=_orig_merge,
    ):
        if proxies is None:
            proxies = {}
        settings = _orig(self, url, proxies, stream, verify, cert)
        settings["verify"] = False
        return settings

    requests.Session.merge_environment_settings = _merge_no_verify
    requests.Session._ssl_patched = True  # type: ignore[attr-defined]

# ===== SEARCH FUNCTIONS =====

def tavily_search_multiple(
    search_queries: List[str],
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    include_images: bool = True,
) -> List[dict]:
    """Perform search using Tavily API for multiple queries.

    Args:
        search_queries: List of search queries to execute
        max_results: Maximum number of results per query
        topic: Topic filter for search results
        include_raw_content: Whether to include raw webpage content
        include_images: Whether to include image URLs in results

    Returns:
        List of search result dictionaries
    """
    # Execute searches sequentially. Note: yon can use AsyncTavilyClient to parallelize this step.
    search_docs = []
    for query in search_queries:
        try:
            result = tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
                include_images=include_images,
            )
        except SSLError as exc:
            # Fallback for environments with self-signed proxy certificates.
            logger.warning(
                "Tavily SSL verification failed for query '%s'; retrying with verify=False: %s",
                query,
                exc,
            )
            _enable_insecure_requests_session()
            result = tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
                include_images=include_images,
            )
        search_docs.append(result)

    return search_docs


def extract_images_from_search_results(
    search_results: List[dict],
) -> list[ImageResult]:
    """Extract deduplicated image metadata from Tavily search responses.

    Handles both plain URL strings and dict-format image entries
    (when Tavily returns descriptions). Populates ``title`` from dict
    entries when available; ``source_page`` is left empty because the
    Tavily API does not attribute images to specific result pages.

    Args:
        search_results: List of raw Tavily search response dicts

    Returns:
        Deduplicated list of ImageResult objects
    """
    seen_urls: set[str] = set()
    images: list[ImageResult] = []

    for response in search_results:
        for img in response.get("images", []):
            if isinstance(img, str):
                url, description, title = img, "", ""
            elif isinstance(img, dict):
                url = img.get("url", "")
                description = img.get("description", "")
                title = img.get("title", "")
            else:
                continue

            if url and url not in seen_urls:
                seen_urls.add(url)
                images.append(
                    ImageResult(
                        url=url,
                        description=description,
                        title=title,
                    )
                )

    return images

def summarize_webpage_content(webpage_content: str) -> str:
    """Summarize webpage content using the configured summarization model.

    Args:
        webpage_content: Raw webpage content to summarize

    Returns:
        Formatted summary with key excerpts
    """
    try:
        # Rebuild the model for each call so expired GenAI tokens are refreshed.
        structured_model = _build_summarization_model().with_structured_output(Summary)

        # Generate summary
        summary = structured_model.invoke([
            HumanMessage(content=summarize_webpage_prompt.format(
                webpage_content=webpage_content,
                date=get_today_str()
            ))
        ])

        # Format summary with clear structure
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )

        return formatted_summary

    except Exception as e:
        logger.warning("Failed to summarize webpage: %s", e)
        return webpage_content[:1000] + "..." if len(webpage_content) > 1000 else webpage_content

def deduplicate_search_results(search_results: List[dict]) -> dict:
    """Deduplicate search results by URL to avoid processing duplicate content.

    Args:
        search_results: List of search result dictionaries

    Returns:
        Dictionary mapping URLs to unique results
    """
    unique_results = {}

    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = result

    return unique_results

def process_search_results(unique_results: dict) -> dict:
    """Process search results by summarizing content where available.

    Args:
        unique_results: Dictionary of unique search results

    Returns:
        Dictionary of processed results with summaries
    """
    summarized_results = {}

    for url, result in unique_results.items():
        # Use existing content if no raw content for summarization
        if not result.get("raw_content"):
            content = result['content']
        else:
            # Summarize raw content for better processing
            content = summarize_webpage_content(result['raw_content'])

        summarized_results[url] = {
            'title': result['title'],
            'content': content
        }

    return summarized_results

def format_search_output(
    summarized_results: dict,
    images: list[ImageResult] | None = None,
) -> str:
    """Format search results into a well-structured string output.

    Args:
        summarized_results: Dictionary of processed results
        images: Optional list of image metadata to append

    Returns:
        Formatted string of search results with clear source separation
    """
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."

    formatted_output = "Search results: \n\n"

    for i, (url, result) in enumerate(summarized_results.items(), 1):
        formatted_output += f"\n\n--- SOURCE {i}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n"

    if images:
        formatted_output += "\n\n--- IMAGES FOUND ---\n"
        for i, img in enumerate(images, 1):
            formatted_output += f"\n[Image {i}]: {img.url}"
            if img.description:
                formatted_output += f"\n  Description: {img.description}"
            formatted_output += "\n"

    return formatted_output


# ===== RESEARCH TOOLS =====

@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
) -> str:
    """Fetch results from Tavily search API with content summarization.

    Args:
        query: A single search query to execute
        max_results: Maximum number of results to return
        topic: Topic to filter results by ('general', 'news', 'finance')

    Returns:
        Formatted string of search results with summaries
    """
    search_results = tavily_search_multiple(
        [query],
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        include_images=True,
    )

    global _last_search_images
    # Extract Tavily-provided images
    _last_search_images = extract_images_from_search_results(search_results)

    unique_results = deduplicate_search_results(search_results)
    summarized_results = process_search_results(unique_results)
    return format_search_output(summarized_results, images=_last_search_images)

@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


# ===== IMAGE DOWNLOAD =====

def download_images(
    images: list[ImageResult],
    output_dir: str | Path,
    timeout: int = 10,
) -> list[ImageResult]:
    """Download images to local disk with best-effort error handling.

    Each image is downloaded individually with a timeout. Failures are
    logged but do not prevent other images from being downloaded.
    A metadata JSON file is written alongside the downloaded images.

    Uses httpx with ``verify=False`` and ``trust_env=False`` to bypass
    corporate SSL inspection and the ``http_proxy`` env var that routes
    http:// URLs through an internal proxy that times out on external hosts.
    Passes ``source_page`` as ``Referer`` to satisfy CDN hotlink protection.

    Args:
        images: List of ImageResult objects to download
        output_dir: Directory to save downloaded images
        timeout: Per-image download timeout in seconds

    Returns:
        Updated list of ImageResult objects with local_path populated
        for successfully downloaded images
    """
    # URL patterns that are never downloadable images — skip without a network call.
    _SKIP_PATTERNS = (
        "lookaside.instagram.com/seo/google_widget",
        "instagram.com/seo/",
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    _VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
    _CONTENT_TYPE_MAP = {
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
        "svg": ".svg",
        "jpeg": ".jpg",
        "jpg": ".jpg",
    }

    updated: list[ImageResult] = []

    with httpx.Client(
        verify=False,
        trust_env=False,
        timeout=float(timeout),
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; research-agent/1.0)"},
    ) as dl_client:
        for idx, img in enumerate(images):
            try:
                if any(p in img.url for p in _SKIP_PATTERNS):
                    logger.debug("Skipping known non-image URL: %s", img.url)
                    updated.append(img)
                    continue

                # Use source_page as Referer to satisfy CDN hotlink checks (420/403).
                referer = img.source_page or img.url
                resp = dl_client.get(img.url, headers={"Referer": referer})
                resp.raise_for_status()

                # Derive filename from URL path
                parsed = urlparse(img.url)
                filename = Path(parsed.path).name or ""
                suffix = Path(filename).suffix.lower() if filename else ""

                if suffix not in _VALID_EXTENSIONS:
                    # Infer extension from Content-Type header
                    content_type = resp.headers.get("content-type", "")
                    ext = None
                    for key, val in _CONTENT_TYPE_MAP.items():
                        if key in content_type:
                            ext = val
                            break
                    if ext is None:
                        logger.warning(
                            "Skipping image with unsupported format: %s "
                            "(content-type: %s)",
                            img.url,
                            content_type,
                        )
                        updated.append(img)
                        continue
                    filename = f"image_{idx:03d}{ext}"
                else:
                    # Prefix index to avoid filename collisions across domains
                    stem = Path(filename).stem
                    filename = f"{idx:03d}_{stem}{suffix}"

                filepath = output_path / filename
                filepath.write_bytes(resp.content)
                updated.append(img.model_copy(update={"local_path": str(filepath)}))
                logger.info("Downloaded image: %s -> %s", img.url, filepath)

            except Exception as e:
                logger.warning("Failed to download image %s: %s", img.url, e)
                updated.append(img)  # keep original without local_path

    # Enrich descriptions for successfully downloaded images via Gemini
    updated = describe_images_with_gemini(updated)

    # Persist structured metadata alongside downloaded images.
    # Only include images with a local_path; only emit url, local_path, description.
    try:
        metadata_path = output_path / "images_metadata.json"
        metadata = [
            {"url": i.url, "local_path": i.local_path, "description": i.description}
            for i in updated
            if i.local_path is not None
        ]
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("Failed to write images_metadata.json: %s", e)

    return updated

# ===== GEMINI IMAGE DESCRIPTION =====

_IMAGE_DESCRIPTION_PROMPT = (
    "Describe this image concisely in 1-3 sentences in Chinese. "
    "If the image shows a product with liquid, include its color, texture, opacity, "
    "and any decorations such as fruit garnish, ice, glass style, or packaging. "
    "Focus on visually distinctive properties."
)


def _image_to_inline_part(path: str) -> dict:
    """Base64-encode a local image file into a Gemini inlineData part."""
    p = Path(path)
    data = p.read_bytes()
    mime, _ = mimetypes.guess_type(p.name)
    if mime is None:
        ext = p.suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")
    return {"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode()}}


def describe_images_with_gemini(images: list[ImageResult]) -> list[ImageResult]:
    """Call Gemini 2.5 flash to generate a description for each downloaded image.

    Reads NANO_BANANA_FLASH_URL from env. If unset, logs a warning and returns
    the input list unchanged. Per-image failures are caught and logged; the image
    is still included with an empty description.

    Args:
        images: List of ImageResult objects (may include items without local_path).

    Returns:
        Updated list with description populated for successfully described images.
    """
    flash_url = os.getenv("NANO_BANANA_FLASH_URL", "").strip()
    if not flash_url:
        logger.warning(
            "NANO_BANANA_FLASH_URL is not set — skipping Gemini image descriptions."
        )
        return images

    genai_token = GenAIToken().token()
    headers = {
        "userid": os.getenv("HEADERS_USERID", ""),
        "project-name": os.getenv("HEADERS_PROJECT_NAME", ""),
        "Authorization": f"Bearer {genai_token}",
    }

    result: list[ImageResult] = []
    for img in images:
        if not img.local_path:
            result.append(img)
            continue
        try:
            payload = {
                "contents": [
                    {
                        "parts": [
                            _image_to_inline_part(img.local_path),
                            {"text": _IMAGE_DESCRIPTION_PROMPT},
                        ]
                    }
                ],
                "config": {"response_modalities": ["text"]},
            }
            with httpx.Client(trust_env=True, timeout=httpx.Timeout(60.0)) as client:
                resp = client.post(url=flash_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            result.append(img.model_copy(update={"description": text}))
            logger.info("Described image: %s", img.local_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to describe image %s: %s", img.local_path, exc)
            result.append(img)

    return result
