"""Recompute and update material_library/index.json from current library files.

Run this after manually editing color.json / decoration.json / texture.json
(e.g. deleting elements) to keep index.json in sync.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def update_index(output_dir: Path) -> None:
    files = {
        "color": output_dir / "color.json",
        "decoration": output_dir / "decoration.json",
        "texture": output_dir / "texture.json",
    }
    index_path = output_dir / "index.json"

    counts: dict[str, int] = {}
    for dim, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing library file: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        counts[dim] = len(data.get("elements", []))

    total = sum(counts.values())

    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    index["total_elements"] = total
    index["color_count"] = counts["color"]
    index["decoration_count"] = counts["decoration"]
    index["texture_count"] = counts["texture"]

    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"index.json updated:")
    print(f"  color:      {counts['color']}")
    print(f"  decoration: {counts['decoration']}")
    print(f"  texture:    {counts['texture']}")
    print(f"  total:      {total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync index.json with current library element counts.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "material_library",
        help="Path to material_library/ directory (default: ../../material_library relative to this script)",
    )
    args = parser.parse_args()
    update_index(args.output_dir)


if __name__ == "__main__":
    main()
