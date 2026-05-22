"""Neo4j query interface for the multi-modal material knowledge graph."""

from __future__ import annotations

from neo4j import Driver

DIMENSION_RELATIONS = {"color": "HAS_COLOR", "texture": "HAS_TEXTURE", "decoration": "HAS_DECORATION"}


def get_images_for_material(
    driver: Driver,
    material_id: str | None = None,
    material_name: str | None = None,
    relation: str | None = None,
    report_id: str | None = None,
) -> list[dict]:
    """Return images connected to a material element.

    Args:
        driver: Neo4j driver.
        material_id: Match by material id (exact).
        material_name: Match by material name (exact).
        relation: One of 'HAS_COLOR', 'HAS_TEXTURE', 'HAS_DECORATION'.
                  If None, matches any relation.
        report_id: Filter images by report_id.

    Returns:
        List of image property dicts (path, description, report_id, filename).
    """
    if material_id is None and material_name is None:
        raise ValueError("Provide either material_id or material_name.")

    rel_clause = f"[:{relation}]" if relation else "[]"
    if material_id:
        mat_match = "{id: $mat_key}"
        mat_key = material_id
    else:
        mat_match = "{name: $mat_key}"
        mat_key = material_name

    report_filter = "AND i.report_id = $report_id" if report_id else ""

    query = (
        f"MATCH (i:Image)-{rel_clause}->(m:Material {mat_match}) "
        f"WHERE 1=1 {report_filter} "
        "RETURN i.path AS path, i.description AS description, "
        "       i.report_id AS report_id, i.filename AS filename"
    )
    params: dict = {"mat_key": mat_key}
    if report_id:
        params["report_id"] = report_id

    with driver.session() as session:
        result = session.run(query, **params)
        return [dict(r) for r in result]


def get_material_image_counts(
    driver: Driver,
    dimension: str | None = None,
) -> list[dict]:
    """Return image counts per material, sorted descending.

    Args:
        driver: Neo4j driver.
        dimension: Filter by dimension label (e.g. '颜色'). None = all.

    Returns:
        List of {material_id, material_name, dimension, image_count} dicts.
    """
    dim_filter = "WHERE m.dimension = $dimension" if dimension else ""
    query = (
        "MATCH (i:Image)-[]->(m:Material) "
        f"{dim_filter} "
        "RETURN m.id AS material_id, m.name AS material_name, "
        "       m.dimension AS dimension, count(i) AS image_count "
        "ORDER BY image_count DESC"
    )
    params = {"dimension": dimension} if dimension else {}
    with driver.session() as session:
        result = session.run(query, **params)
        return [dict(r) for r in result]
