"""Multi-modal Knowledge Graph builder: images ↔ material trend elements."""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

import httpx
from neo4j import Driver, GraphDatabase
from pydantic import BaseModel
from tqdm import tqdm

from deep_research_from_scratch.Helper import GenAIToken

logger = logging.getLogger(__name__)

DIMENSION_RELATION = {
    "color": "HAS_COLOR",
    "texture": "HAS_TEXTURE",
    "decoration": "HAS_DECORATION",
}

DIMENSION_LABEL = {
    "color": "颜色",
    "texture": "透明度与质地",
    "decoration": "装饰物",
}


# ── Neo4j connection ──────────────────────────────────────────────────────────

def get_neo4j_driver() -> Driver:
    """Create Neo4j driver from environment variables."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    if not password:
        raise ValueError(f"NEO4J_PASSWORD is not set. URI: {uri}")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        raise ConnectionError(
            f"Cannot connect to Neo4j at {uri}. Is Neo4j running?\n{e}"
        ) from e


# ── Schema initialisation ─────────────────────────────────────────────────────

def init_kg_schema(driver: Driver) -> None:
    """Create unique constraints for Image.path, SkippedImage.path, and Material.id."""
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS "
            "FOR (i:Image) REQUIRE i.path IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS "
            "FOR (s:SkippedImage) REQUIRE s.path IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS "
            "FOR (m:Material) REQUIRE m.id IS UNIQUE"
        )
    logger.info("Neo4j schema constraints created.")


# ── Node upsert ───────────────────────────────────────────────────────────────

def upsert_image_nodes(driver: Driver, images_meta: list[dict]) -> None:
    """MERGE Image nodes into Neo4j."""
    query = (
        "UNWIND $rows AS row "
        "MERGE (i:Image {path: row.path}) "
        "SET i.description = row.description, "
        "    i.report_id   = row.report_id, "
        "    i.filename    = row.filename"
    )
    rows = [
        {
            "path": m["local_path"],
            "description": m.get("description", ""),
            "report_id": m.get("report_id", ""),
            "filename": Path(m["local_path"]).name,
        }
        for m in images_meta
    ]
    with driver.session() as session:
        session.run(query, rows=rows)
    logger.info("Upserted %d Image nodes.", len(rows))


def upsert_material_nodes(driver: Driver, materials: dict[str, list[dict]]) -> None:
    """MERGE Material nodes into Neo4j."""
    query = (
        "UNWIND $rows AS row "
        "MERGE (m:Material {id: row.id}) "
        "SET m.name            = row.name, "
        "    m.name_en         = row.name_en, "
        "    m.dimension       = row.dimension, "
        "    m.dimension_key   = row.dimension_key, "
        "    m.visual_keywords = row.visual_keywords, "
        "    m.signals         = row.signals, "
        "    m.typical_use     = row.typical_use, "
        "    m.product_category = row.product_category"
    )
    rows = []
    for dim_key, elements in materials.items():
        for el in elements:
            rows.append({
                "id": el["id"],
                "name": el["name"],
                "name_en": el.get("name_en", ""),
                "dimension": el["dimension"],
                "dimension_key": dim_key,
                "visual_keywords": el.get("visual_keywords", []),
                "signals": el.get("signals", []),
                "typical_use": el.get("typical_use", ""),
                "product_category": el.get("product_category", ""),
            })
    with driver.session() as session:
        session.run(query, rows=rows)
    logger.info("Upserted %d Material nodes.", len(rows))


# ── VLM helpers ───────────────────────────────────────────────────────────────

class DimensionMatches(BaseModel):
    """Structured output for VLM closed-set classification."""

    matched_material_ids: list[str]


_VISIBILITY_PROMPT = """You are an expert in beauty product visual analysis.
Look at this product image and decide whether any product formula or contents are \
CLEARLY VISIBLE — e.g. liquid, cream, lotion, gel, serum, powder, scrub particles, \
balm, oil, foam, emulsion, or any similar material body (料体).

Answer with JSON only. Examples:
  {"has_visible_content": true}   ← product formula is clearly visible
  {"has_visible_content": false}  ← only closed packaging, bottle exterior, or no product shown
"""

_MATCH_SYSTEM_PROMPT = """You are an expert in beauty product visual analysis.
Your task: analyse the CONTENTS of a product image (liquid, cream, gel, scrub particles etc.)
and identify which trend material elements are visually represented.

IMPORTANT rules:
- Focus ONLY on the product contents (liquid colour, texture, decorative particles etc.)
- IGNORE outer packaging, bottle shape, labels, box design
- Return ONLY material IDs from the provided list — do not invent new IDs
- It is OK to return an empty list if nothing matches
- It is OK to return multiple IDs if multiple materials are visually present in the contents
"""

def _image_to_inline_part(path: str) -> dict:
    """Base64-encode a local image file into a Gemini inlineData part."""
    import mimetypes
    p = Path(path)
    data = p.read_bytes()
    mime, _ = mimetypes.guess_type(p.name)
    if mime is None:
        ext = p.suffix.lower()
        mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
        }.get(ext, "image/jpeg")
    return {"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode()}}


def check_has_visible_content(
    image_path: str,
    url: str,
    headers: dict,
) -> bool:
    """Single VLM call: does this image show visible product formula/contents?

    Returns True if product material body (料体) is clearly visible, False otherwise.
    On any error, defaults to True (proceed with matching) to avoid silent data loss.
    """
    contents = [
        {
            "parts": [
                _image_to_inline_part(image_path),
                {"text": _VISIBILITY_PROMPT},
            ]
        }
    ]
    payload = {
        "contents": contents,
        "config": {"response_modalities": ["text"]},
    }
    try:
        with httpx.Client(trust_env=True, timeout=httpx.Timeout(60.0)) as client:
            resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()
        parsed = json.loads(text)
        return bool(parsed.get("has_visible_content", True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Visibility check failed for %s: %s — defaulting to True", image_path, exc)
        return True


def _mark_no_content(driver: Driver, image_path: str) -> None:
    """Create a SkippedImage node so this path is never reprocessed."""
    with driver.session() as session:
        session.run(
            "MERGE (:SkippedImage {path: $path})",
            path=image_path,
        )



def build_dimension_prompt(
    image_path: str,
    materials: list[dict],
    dimension_label: str,
) -> list[dict]:
    """Build Gemini contents payload for closed-set dimension matching."""
    mat_lines = []
    for m in materials:
        kws = ", ".join(m.get("visual_keywords", [])[:10])
        mat_lines.append(f'- ID: {m["id"]} | Name: {m["name"]} | Keywords: {kws}')
    mat_text = "\n".join(mat_lines)

    prompt_text = (
        f"{_MATCH_SYSTEM_PROMPT}\n\n"
        f"Dimension: {dimension_label}\n\n"
        f"Material candidates:\n{mat_text}\n\n"
        "Look at the image. Which of the above materials are visually present in "
        "the product contents?\n"
        'Return JSON only: {"matched_material_ids": ["id1", "id2"]}'
    )
    return [
        {
            "parts": [
                _image_to_inline_part(image_path),
                {"text": prompt_text},
            ]
        }
    ]


def _call_vlm_once(
    url: str,
    headers: dict,
    contents: list[dict],
    valid_ids: set[str],
) -> list[str]:
    """Call VLM once and return list of valid matched material IDs."""
    payload = {
        "contents": contents,
        "config": {"response_modalities": ["text"]},
    }
    with httpx.Client(trust_env=True, timeout=httpx.Timeout(60.0)) as client:
        resp = client.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
        .strip()
    )
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        text = text.rstrip("`").strip()
    try:
        parsed = json.loads(text)
        ids = parsed.get("matched_material_ids", [])
        return [i for i in ids if i in valid_ids]
    except json.JSONDecodeError:
        logger.warning("VLM returned non-JSON: %s", text[:200])
        return []


def run_vlm_match(
    image_path: str,
    materials: dict[str, list[dict]],
) -> dict[str, list[list[str]]]:
    """Run VLM 3×3 matching for one image across all three dimensions.

    Returns:
        {dimension_key: [run1_ids, run2_ids, run3_ids]}
    """
    nano_url = os.getenv("NANO_BANANA_URL", "").strip()
    if not nano_url:
        raise ValueError("NANO_BANANA_URL is not set.")

    headers = {
        "userid": os.getenv("HEADERS_USERID", ""),
        "project-name": os.getenv("HEADERS_PROJECT_NAME", ""),
        "Authorization": f"Bearer {GenAIToken().token()}",
    }

    results: dict[str, list[list[str]]] = {}
    for dim_key, dim_materials in materials.items():
        valid_ids = {m["id"] for m in dim_materials}
        contents = build_dimension_prompt(image_path, dim_materials, DIMENSION_LABEL[dim_key])
        runs = []
        for _ in range(3):
            try:
                matched = _call_vlm_once(nano_url, headers, contents, valid_ids)
                runs.append(matched)
            except Exception as exc:  # noqa: BLE001
                logger.warning("VLM call failed for %s / %s: %s", image_path, dim_key, exc)
                runs.append([])
        results[dim_key] = runs

    return results


def compute_consensus(runs: list[list[str]]) -> list[str]:
    """Return material IDs that appear in at least 2 out of 3 VLM runs."""
    if len(runs) < 3:
        return []
    from collections import Counter
    counts = Counter(mid for run in runs for mid in set(run))
    return [mid for mid, cnt in counts.items() if cnt >= 2]


def upsert_edges(
    driver: Driver,
    image_path: str,
    consensus_by_dim: dict[str, list[str]],
) -> None:
    """Write consensus-matched edges into Neo4j."""
    with driver.session() as session:
        for dim_key, material_ids in consensus_by_dim.items():
            rel_type = DIMENSION_RELATION[dim_key]
            for mat_id in material_ids:
                session.run(
                    f"MATCH (i:Image {{path: $path}}), (m:Material {{id: $mat_id}}) "
                    f"MERGE (i)-[:{rel_type}]->(m)",
                    path=image_path,
                    mat_id=mat_id,
                )


def get_processed_image_paths(driver: Driver) -> set[str]:
    """Return paths of Image nodes already fully processed (present in Neo4j)."""
    with driver.session() as session:
        result = session.run("MATCH (i:Image) RETURN i.path AS path")
        return {record["path"] for record in result}


# ── Material sync ─────────────────────────────────────────────────────────────

def sync_materials(
    driver: Driver,
    materials: dict[str, list[dict]],
) -> dict[str, list[str]]:
    """Sync Neo4j Material nodes against the current JSON files.

    - Materials present in JSON but missing from Neo4j → upserted.
    - Materials present in Neo4j but missing from JSON → deleted (DETACH DELETE
      removes all edges to Image nodes automatically).

    Returns:
        {"added": [...ids], "removed": [...ids]}
    """
    all_current = {m["id"]: m for dim_mats in materials.values() for m in dim_mats}

    with driver.session() as session:
        result = session.run("MATCH (m:Material) RETURN m.id AS id")
        existing_ids = {record["id"] for record in result}

    added_ids = set(all_current) - existing_ids
    removed_ids = existing_ids - set(all_current)

    if removed_ids:
        with driver.session() as session:
            session.run(
                "MATCH (m:Material) WHERE m.id IN $ids DETACH DELETE m",
                ids=list(removed_ids),
            )
        logger.info("Removed %d Material nodes: %s", len(removed_ids), removed_ids)

    if added_ids:
        added_by_dim: dict[str, list[dict]] = {k: [] for k in materials}
        for dim_key, dim_mats in materials.items():
            added_by_dim[dim_key] = [m for m in dim_mats if m["id"] in added_ids]
        upsert_material_nodes(driver, added_by_dim)
        logger.info("Added %d Material nodes: %s", len(added_ids), added_ids)

    return {"added": list(added_ids), "removed": list(removed_ids)}


def reset_orphaned_images(driver: Driver) -> list[str]:
    """Delete Image nodes that have no outgoing edges.

    These images lost all their material connections (e.g. because their matched
    materials were removed). Deleting them allows build_kg() to reprocess them
    against the current material set on the next run.

    Returns:
        List of image paths that were reset.
    """
    with driver.session() as session:
        result = session.run(
            "MATCH (i:Image) WHERE NOT (i)-[]->() "
            "WITH collect(i.path) AS paths, collect(i) AS nodes "
            "FOREACH (n IN nodes | DETACH DELETE n) "
            "RETURN paths"
        )
        record = result.single()
        paths = record["paths"] if record else []
    if paths:
        logger.info("Reset %d orphaned Image nodes for reprocessing.", len(paths))
    return paths


def build_kg(
    driver: Driver,
    images_meta: list[dict],
    materials: dict[str, list[dict]],
    dry_run: bool = False,
) -> None:
    """Run full KG building pipeline with incremental skip for existing images."""
    init_kg_schema(driver)
    upsert_material_nodes(driver, materials)

    # "done" = Image nodes (visible content, edges built) OR SkippedImage nodes (no content)
    with driver.session() as session:
        result = session.run(
            "MATCH (n) WHERE n:Image OR n:SkippedImage RETURN n.path AS path"
        )
        done_paths = {record["path"] for record in result}

    new_images = [m for m in images_meta if m["local_path"] not in done_paths]
    logger.info(
        "Images to process: %d (skipping %d already done)",
        len(new_images), len(done_paths),
    )

    if dry_run:
        logger.info("Dry run — skipping VLM calls.")
        return

    for img_meta in tqdm(new_images, desc="Building KG edges"):
        image_path = img_meta["local_path"]
        try:
            nano_url = os.getenv("NANO_BANANA_URL", "").strip()
            headers = {
                "userid": os.getenv("HEADERS_USERID", ""),
                "project-name": os.getenv("HEADERS_PROJECT_NAME", ""),
                "Authorization": f"Bearer {GenAIToken().token()}",
            }
            if not check_has_visible_content(image_path, nano_url, headers):
                logger.info("No visible content — skipping %s", image_path)
                _mark_no_content(driver, image_path)
                continue
            # Only insert the Image node after confirming visible content
            upsert_image_nodes(driver, [img_meta])
            runs_by_dim = run_vlm_match(image_path, materials)
            consensus_by_dim = {
                dim: compute_consensus(runs)
                for dim, runs in runs_by_dim.items()
            }
            upsert_edges(driver, image_path, consensus_by_dim)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to process %s: %s", image_path, exc)
