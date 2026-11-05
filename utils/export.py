"""CSV and JSON output helpers."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def export_items(items: list[dict], path: Path) -> int:
    """Write records based on a .csv or .json extension."""
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".json"}:
        raise ValueError("Output file must end in .csv or .json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".json":
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        fields = list(dict.fromkeys(key for item in items for key in item))
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            if fields:
                writer.writeheader()
            writer.writerows({key: " | ".join(map(str, value)) if isinstance(value, list) else value
                              for key, value in item.items()} for item in items)
    return len(items)
