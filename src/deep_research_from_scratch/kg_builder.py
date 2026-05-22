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
    """Create unique constraints for Image.path and Material.id."""
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS "
            "FOR (i:Image) REQUIRE i.path IS UNIQUE"
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


def _image_to_base64(image_path: str) -> tuple[str, str]:
    """Return (base64_data, mime_type) for an image file."""
    path = Path(image_path)
    suffix = path.suffix.lower().lstrip(".")
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "gif": "image/gif", "bmp": "image/bmp",
    }
    mime = mime_map.get(suffix, "image/jpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return b64, mime


_MATCH_SYSTEM_PROMPT = """You are an expert in beauty product visual analysis.
Your task: analyse the CONTENTS of a product image (liquid, cream, gel, scrub particles etc.)
and identify which trend material elements are visually represented.

IMPORTANT rules:
- Focus ONLY on the product contents (liquid colour, texture, decorative particles etc.)
- IGNORE outer packaging, bottle shape, labels, box design
- Return ONLY material IDs from the provided list — do not invent new IDs
- It is OK to return an empty list if nothing matches
"""

def build_dimension_prompt(
    image_b64: str,
    mime_type: str,
    materials: list[dict],
    dimension_label: str,
) -> list[dict]:
    """Build Gemini contents payload for closed-set dimension matching."""
    # Format material list compactly
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
        "Return JSON: {\"matched_material_ids\": [\"id1\", \"id2\"]}"
    )
    return [
        {
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                {"text": prompt_text},
            ]
        }
    ]


async def _call_vlm_once(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    contents: list[dict],
    valid_ids: set[str],
) -> list[str]:
    """Call VLM once and return list of valid matched material IDs."""
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }
    resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
        .strip()
    )
    try:
        parsed = json.loads(text)
        ids = parsed.get("matched_material_ids", [])
        # Filter to only valid IDs from the candidate list
        return [i for i in ids if i in valid_ids]
    except json.JSONDecodeError:
        logger.warning("VLM returned non-JSON: %s", text[:200])
        return []


async def run_vlm_match(
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

    token = GenAIToken().token()
    headers = {
        "Authorization": f"Bearer {token}",
        "userid": os.getenv("HEADERS_USERID", ""),
        "project-name": os.getenv("HEADERS_PROJECT_NAME", ""),
        "Content-Type": "application/json",
    }

    image_b64, mime_type = _image_to_base64(image_path)
    results: dict[str, list[list[str]]] = {}

    async with httpx.AsyncClient(trust_env=True) as client:
        for dim_key, dim_materials in materials.items():
            valid_ids = {m["id"] for m in dim_materials}
            contents = build_dimension_prompt(
                image_b64, mime_type, dim_materials, DIMENSION_LABEL[dim_key]
            )
            runs = []
            for _ in range(3):
                try:
                    matched = await _call_vlm_once(client, nano_url, headers, contents, valid_ids)
                    runs.append(matched)
                except Exception as exc:
                    logger.warning("VLM call failed for %s / %s: %s", image_path, dim_key, exc)
                    runs.append([])
            results[dim_key] = runs

    return results


def compute_consensus(runs: list[list[str]]) -> list[str]:
    """Return material IDs that appear in ALL three VLM runs."""
    if not runs or any(len(r) == 0 and len(runs[0]) > 0 for r in runs):
        # If any run errored (empty) but others had results, be conservative
        pass
    if len(runs) < 3:
        return []
    sets = [set(r) for r in runs]
    consensus = sets[0].intersection(*sets[1:])
    return list(consensus)


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


# ── Full pipeline ─────────────────────────────────────────────────────────────

async def build_kg(
    driver: Driver,
    images_meta: list[dict],
    materials: dict[str, list[dict]],
    dry_run: bool = False,
) -> None:
    """Run full KG building pipeline with incremental skip for existing images."""
    init_kg_schema(driver)
    upsert_image_nodes(driver, images_meta)
    upsert_material_nodes(driver, materials)

    # An image is considered "done" if it has at least one outgoing relationship
    with driver.session() as session:
        result = session.run(
            "MATCH (i:Image)-[r]->() RETURN DISTINCT i.path AS path"
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
            runs_by_dim = await run_vlm_match(image_path, materials)
            consensus_by_dim = {
                dim: compute_consensus(runs)
                for dim, runs in runs_by_dim.items()
            }
            upsert_edges(driver, image_path, consensus_by_dim)
        except Exception as exc:
            logger.error("Failed to process %s: %s", image_path, exc)
