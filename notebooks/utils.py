from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import json
import os
from typing import Literal

from pydantic import BaseModel, Field

console = Console()


# ---------------------------------------------------------------------------
# Shared evaluation helpers — used across notebook eval sections
# ---------------------------------------------------------------------------

class JudgeResult(BaseModel):
    """Structured output schema for LLM-as-judge evaluators.

    Fields are ordered so the judge must produce evidence before scoring,
    which improves scoring reliability.
    """

    evidence: str = Field(
        description=(
            "Specific quotes, observations, or data points from the artifact "
            "that support the assessment. Must be populated BEFORE the score."
        ),
    )
    reasoning: str = Field(
        description=(
            "Explanation of why the artifact deserves the score, referencing "
            "the rubric level and the evidence provided."
        ),
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Integer score on the balanced 1–5 rubric.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Self-assessed confidence in the judgment.",
    )


class JudgeResultWithImprovement(JudgeResult):
    """Extended judge result that includes an improvement suggestion."""

    improvement_note: str = Field(
        description="One concrete suggestion for how the artifact could be improved.",
    )


def normalize_score(raw: int) -> float:
    """Normalize a 1–5 rubric score to 0.0–1.0.

    Mapping: 1→0.0, 2→0.25, 3→0.5, 4→0.75, 5→1.0.
    """
    return (raw - 1) / 4


def to_langfuse_evaluation(
    key: str,
    judge_result: JudgeResult,
    *,
    prompt_name: str | None = None,
    judge_model: str | None = None,
    evaluator_type: str = "direct_scoring",
    rubric_strictness: str = "balanced",
):
    """Convert a JudgeResult into a Langfuse ``Evaluation`` object.

    Returns an ``Evaluation`` compatible with ``Langfuse.run_experiment()``
    evaluators.

    Args:
        key: Evaluator metric name (e.g. ``"research_depth_score"``).
        judge_result: Parsed judge output.
        prompt_name: Name of the prompt template used.
        judge_model: Model identifier used for judging.
        evaluator_type: One of ``"heuristic"``, ``"direct_scoring"``, ``"pairwise"``.
        rubric_strictness: Rubric strictness level (default ``"balanced"``).

    Returns:
        ``langfuse.Evaluation`` object with ``name``, ``value``,
        ``comment``, and ``metadata`` populated.
    """
    from langfuse import Evaluation

    comment = (
        f"Evidence: {judge_result.evidence}\n\n"
        f"Reasoning: {judge_result.reasoning}\n\n"
        f"Confidence: {judge_result.confidence}"
    )

    if hasattr(judge_result, "improvement_note"):
        comment += f"\n\nImprovement: {judge_result.improvement_note}"

    metadata: dict = {
        "evaluator_type": evaluator_type,
        "rubric_strictness": rubric_strictness,
        "raw_score": judge_result.score,
        "confidence": judge_result.confidence,
    }
    if prompt_name:
        metadata["prompt_name"] = prompt_name
    if judge_model:
        metadata["judge_model"] = judge_model

    return Evaluation(
        name=key,
        value=normalize_score(judge_result.score),
        comment=comment,
        metadata=metadata,
    )


def init_langfuse():
    """Initialize a Langfuse client with fail-fast validation.

    Reads ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and the
    host URL (``LANGFUSE_HOST`` or ``LANGFUSE_BASE_URL``) from the
    environment.  Raises immediately if credentials are missing so
    notebooks surface a clear error instead of silently creating a
    disabled client.

    Returns:
        A configured ``langfuse.Langfuse`` instance.
    """
    from langfuse import Langfuse

    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")

    missing = []
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        missing.append("LANGFUSE_PUBLIC_KEY")
    if not os.getenv("LANGFUSE_SECRET_KEY"):
        missing.append("LANGFUSE_SECRET_KEY")
    if not host:
        missing.append("LANGFUSE_HOST (or LANGFUSE_BASE_URL)")
    if missing:
        raise EnvironmentError(
            f"Langfuse credentials not configured. "
            f"Missing env vars: {', '.join(missing)}. "
            f"Set them in your .env file."
        )

    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=host,
    )


def disable_langsmith():
    """Remove LangSmith tracing env vars so traces go only to Langfuse.

    Call immediately after ``load_dotenv()`` and before any LangChain
    model or graph construction.
    """
    for key in (
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_API_KEY",
    ):
        os.environ.pop(key, None)


def init_langfuse_tracing():
    """Create a Langfuse CallbackHandler for LangChain/LangGraph tracing.

    Validates credentials via ``init_langfuse()`` before constructing
    the handler so missing keys surface immediately.

    Returns:
        A ``langfuse.langchain.CallbackHandler`` instance.  Pass it in
        the ``config["callbacks"]`` list when invoking a chain or graph.
    """
    from langfuse.langchain import CallbackHandler

    init_langfuse()
    return CallbackHandler()


def init_judge_model(
    model: str = "azure_openai:GPT-54-2026-03-05",
    temperature: float = 0.0,
):
    """Initialize the LLM used for judge evaluations.

    Extracts the Azure deployment name from the model identifier string
    (e.g. ``"azure_openai:GPT-54-2026-03-05"`` → deployment
    ``"GPT-54-2026-03-05"``), matching the ``_build_model`` pattern used
    by the research agent.

    Args:
        model: Model identifier (default is the spec-designated judge model).
        temperature: Sampling temperature (default 0.0 for deterministic judging).

    Returns:
        A chat model instance ready for ``.invoke()`` or ``.with_structured_output()``.
    """
    from langchain.chat_models import init_chat_model as _init_chat_model
    from deep_research_from_scratch.Helper import GenAIToken

    deployment = model.split(":")[-1]

    return _init_chat_model(
        model=model,
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

def format_message_content(message):
    """Convert message content to displayable string"""
    parts = []
    tool_calls_processed = False
    
    # Handle main content
    if isinstance(message.content, str):
        parts.append(message.content)
    elif isinstance(message.content, list):
        # Handle complex content like tool calls (Anthropic format)
        for item in message.content:
            if item.get('type') == 'text':
                parts.append(item['text'])
            elif item.get('type') == 'tool_use':
                parts.append(f"\n🔧 Tool Call: {item['name']}")
                parts.append(f"   Args: {json.dumps(item['input'], indent=2)}")
                parts.append(f"   ID: {item.get('id', 'N/A')}")
                tool_calls_processed = True
    else:
        parts.append(str(message.content))
    
    # Handle tool calls attached to the message (OpenAI format) - only if not already processed
    if not tool_calls_processed and hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
            parts.append(f"\n🔧 Tool Call: {tool_call['name']}")
            parts.append(f"   Args: {json.dumps(tool_call['args'], indent=2)}")
            parts.append(f"   ID: {tool_call['id']}")
    
    return "\n".join(parts)


def format_messages(messages):
    """Format and display a list of messages with Rich formatting"""
    for m in messages:
        msg_type = m.__class__.__name__.replace('Message', '')
        content = format_message_content(m)

        if msg_type == 'Human':
            console.print(Panel(content, title="🧑 Human", border_style="blue"))
        elif msg_type == 'Ai':
            console.print(Panel(content, title="🤖 Assistant", border_style="green"))
        elif msg_type == 'Tool':
            console.print(Panel(content, title="🔧 Tool Output", border_style="yellow"))
        else:
            console.print(Panel(content, title=f"📝 {msg_type}", border_style="white"))


def format_message(messages):
    """Alias for format_messages for backward compatibility"""
    return format_messages(messages)


def show_prompt(prompt_text: str, title: str = "Prompt", border_style: str = "blue"):
    """
    Display a prompt with rich formatting and XML tag highlighting.
    
    Args:
        prompt_text: The prompt string to display
        title: Title for the panel (default: "Prompt")
        border_style: Border color style (default: "blue")
    """
    # Create a formatted display of the prompt
    formatted_text = Text(prompt_text)
    formatted_text.highlight_regex(r'<[^>]+>', style="bold blue")  # Highlight XML tags
    formatted_text.highlight_regex(r'##[^#\n]+', style="bold magenta")  # Highlight headers
    formatted_text.highlight_regex(r'###[^#\n]+', style="bold cyan")  # Highlight sub-headers

    # Display in a panel for better presentation
    console.print(Panel(
        formatted_text, 
        title=f"[bold green]{title}[/bold green]",
        border_style=border_style,
        padding=(1, 2)
    ))