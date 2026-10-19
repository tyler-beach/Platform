"""Deterministic suggestion heuristics — never approve."""

from __future__ import annotations

import re
from typing import Any

EXCEED_RE = re.compile(
    r"MUST\s+NOT\s+exceed\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
AT_LEAST_RE = re.compile(
    r"MUST\s+be\s+at\s+least\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
WITHIN_RE = re.compile(
    r"within\s+(\d+(?:\.\d+)?)\s+days?",
    re.IGNORECASE,
)
MUST_RE = re.compile(r"\bMUST\b", re.IGNORECASE)


def suggest_from_decision(decision: str, known_predicates: set[str] | None = None) -> dict[str, Any]:
    """Return suggestion fields only. Never sets approval_state."""
    out: dict[str, Any] = {"suggestion_source": "heuristic"}
    if not decision.strip():
        return out

    m = EXCEED_RE.search(decision)
    if m:
        out["kind"] = "numeric_max"
        out["limit"] = _num(m.group(1))
        return out

    m = AT_LEAST_RE.search(decision)
    if m:
        out["kind"] = "numeric_min"
        out["limit"] = _num(m.group(1))
        return out

    m = WITHIN_RE.search(decision)
    if m and MUST_RE.search(decision):
        out["kind"] = "numeric_max"
        out["limit"] = _num(m.group(1))
        return out

    if MUST_RE.search(decision):
        out["kind"] = "boolean_required"

    if known_predicates:
        lowered = decision.lower()
        hits = [p for p in sorted(known_predicates) if p.lower() in lowered or p.replace(".", " ") in lowered]
        if len(hits) == 1:
            out["predicate"] = hits[0]
    return out


def _num(raw: str) -> float | int:
    if "." in raw:
        return float(raw)
    return int(raw)
