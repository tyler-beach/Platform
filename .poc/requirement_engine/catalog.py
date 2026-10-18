"""Load the approved typed-requirement catalog."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import engine
import predicate_registry

CATALOG_DIR = Path(__file__).resolve().parents[1] / "requirement_catalog"
REQUIREMENTS_PATH = CATALOG_DIR / "requirements.jsonl"


def load_requirements(path: str | Path | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path else REQUIREMENTS_PATH
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("approval_state") != "approved":
            raise ValueError(f"requirements.jsonl:{line_no} is not approved")
        if item.get("kind") not in engine.KINDS:
            raise ValueError(f"requirements.jsonl:{line_no} unsupported kind {item.get('kind')!r}")
        predicate_registry.asserts_compatible(item["kind"], item["predicate"])
        rows.append(item)
    ids = [row["requirement_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate requirement_id in catalog")
    return rows


def requirement_for_engine(row: dict[str, Any]) -> dict[str, Any]:
    req = {
        "requirement_id": row["requirement_id"],
        "kind": row["kind"],
        "predicate": row["predicate"],
        "subject": row["subject"],
    }
    if "limit" in row:
        req["limit"] = row["limit"]
    if "approved_set" in row:
        req["approved_set"] = list(row["approved_set"])
    return req
