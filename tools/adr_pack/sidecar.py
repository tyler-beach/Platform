"""Typed requirement sidecars (.req.json) — stdlib JSON only."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .heuristics import suggest_from_decision
from .parse import ParsedADR

KINDS = {
    "numeric_max",
    "numeric_min",
    "resource_present",
    "boolean_required",
    "set_membership",
    "dependency_forbidden",
}

REQUIRED_BUILD_FIELDS = (
    "adr_id",
    "requirement_id",
    "title",
    "domain",
    "lifecycle_status",
    "kind",
    "predicate",
    "subject",
    "decision",
    "approval_state",
)


def sidecar_path_for(adr_path: Path) -> Path:
    return adr_path.with_name(adr_path.name + ".req.json")


def load_sidecar(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: sidecar must be a JSON object")
    return data


def is_approved_complete(sidecar: dict[str, Any]) -> bool:
    if sidecar.get("approval_state") != "approved":
        return False
    for field in REQUIRED_BUILD_FIELDS:
        if not str(sidecar.get(field, "")).strip():
            return False
    if sidecar.get("kind") not in KINDS:
        return False
    app = sidecar.get("applicability") or {}
    domains = app.get("domains") if isinstance(app, dict) else None
    if not domains:
        return False
    if sidecar.get("label_status") == "needs_human_typing":
        return False
    return True


def draft_sidecar(
    parsed: ParsedADR,
    *,
    known_predicates: set[str] | None = None,
    use_heuristics: bool = True,
) -> dict[str, Any]:
    adr_id = parsed.adr_id or slug_id(parsed.path.stem)
    decision = parsed.decision
    domain = parsed.domain
    status = normalize_lifecycle(parsed.status)
    title = parsed.title or parsed.path.stem

    row: dict[str, Any] = {
        "schema_version": "pathfinder-adr-sidecar-v1",
        "adr_id": adr_id,
        "requirement_id": f"{adr_id}-REQ-1",
        "title": title,
        "domain": domain,
        "lifecycle_status": status or "accepted",
        "decision": decision,
        "kind": "",
        "predicate": "",
        "subject": "",
        "applicability": {"domains": [domain] if domain else []},
        "approval_state": "draft",
        "label_status": "needs_human_typing",
        "source_span": {
            "path": parsed.path.as_posix(),
            "excerpt": decision[:500],
        },
    }
    if use_heuristics:
        suggestions = suggest_from_decision(decision, known_predicates)
        for key in ("kind", "limit", "predicate"):
            if key in suggestions and suggestions[key] not in (None, ""):
                if key == "kind" and not row["kind"]:
                    row["kind"] = suggestions["kind"]
                elif key == "limit":
                    row["limit"] = suggestions["limit"]
                elif key == "predicate" and not row["predicate"]:
                    row["predicate"] = suggestions["predicate"]
        if suggestions.get("suggestion_source") == "heuristic" and (
            row.get("kind") or row.get("limit") or row.get("predicate")
        ):
            row["suggestion_source"] = "heuristic"
            row["review_notes"] = (
                "Heuristic suggestions only. Fill predicate/subject/kind, "
                "set label_status to a reviewed value, and approval_state=approved "
                "before pack build."
            )
    return row


def write_sidecar(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_lifecycle(status: str) -> str:
    s = status.lower()
    s = re.sub(r"\s*\(.*?\)\s*", " ", s).strip()
    if "accept" in s or s == "active":
        return "accepted"
    if "propos" in s or "draft" in s:
        return "proposed"
    if "super" in s or "retir" in s or "reject" in s or "deprecat" in s:
        return "superseded"
    return s.split()[0] if s else ""


def slug_id(stem: str) -> str:
    m = re.search(r"(ADR[-_][A-Z0-9][-A-Z0-9]*)", stem, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace("_", "-")
    return stem.upper()
