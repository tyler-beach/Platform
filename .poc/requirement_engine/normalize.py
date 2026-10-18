"""Validate typed ADR requirement candidates before shared evaluation.

AI or humans may propose structure. Validation and approval decide usability.
This module does not parse arbitrary ADR prose or manufacture evidence.
"""
from __future__ import annotations

from typing import Any

import engine
import predicate_registry

NORMALIZER_VERSION = "requirement-normalizer-v1"
APPROVAL_STATES = {"proposed", "approved", "rejected", "unnormalized"}
REQUIRED_STRING_FIELDS = ("requirement_id", "kind", "predicate", "subject", "adr_id", "adr_revision")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_candidate(candidate: Any) -> list[str]:
    """Return validation issues; empty list means structurally eligible for approval."""
    issues: list[str] = []
    if not isinstance(candidate, dict):
        return ["candidate must be an object"]
    for field in REQUIRED_STRING_FIELDS:
        if not _nonempty_string(candidate.get(field)):
            issues.append(f"missing or empty {field}")
    kind = candidate.get("kind")
    if kind not in engine.KINDS:
        issues.append(f"unsupported kind: {kind!r}")
    predicate = candidate.get("predicate")
    if _nonempty_string(predicate):
        try:
            predicate_registry.get_predicate(predicate)
            if kind in engine.KINDS:
                predicate_registry.asserts_compatible(kind, predicate)
        except predicate_registry.CapabilityError as exc:
            issues.append(str(exc))
    if kind == "numeric_max" and (type(candidate.get("limit")) not in (int, float) or isinstance(candidate.get("limit"), bool) or candidate.get("limit", -1) < 0):
        issues.append("numeric_max requires a non-negative numeric limit")
    if kind == "set_membership":
        approved = candidate.get("approved_set")
        if not isinstance(approved, list) or not approved or any(not _nonempty_string(x) for x in approved):
            issues.append("set_membership requires a non-empty approved_set of strings")
    span = candidate.get("source_span")
    if not isinstance(span, dict):
        issues.append("missing or invalid source_span")
    elif not _nonempty_string(span.get("path")) or not _nonempty_string(span.get("excerpt")):
        issues.append("source_span requires path and excerpt")
    return issues


def normalize(candidate: Any, *, approval_state: str = "proposed", approved_by: str | None = None) -> dict[str, Any]:
    """Produce a normalized requirement record with explicit approval semantics."""
    if approval_state not in APPROVAL_STATES:
        raise ValueError(f"invalid approval_state: {approval_state!r}")
    issues = validate_candidate(candidate)
    if approval_state == "approved" and issues:
        raise ValueError("cannot approve invalid requirement candidate: " + "; ".join(issues))
    if approval_state == "approved" and not _nonempty_string(approved_by):
        raise ValueError("approved requirements require approved_by")
    if issues and approval_state == "proposed":
        state = "unnormalized"
    else:
        state = approval_state
    record = {
        "normalizer_version": NORMALIZER_VERSION,
        "approval_state": state,
        "validation_issues": issues,
        "approved_by": approved_by if state == "approved" else None,
        "requirement": {
            key: candidate[key]
            for key in ("requirement_id", "kind", "predicate", "subject")
            if isinstance(candidate, dict) and key in candidate
        },
        "provenance": {
            "adr_id": candidate.get("adr_id") if isinstance(candidate, dict) else None,
            "adr_revision": candidate.get("adr_revision") if isinstance(candidate, dict) else None,
            "source_span": candidate.get("source_span") if isinstance(candidate, dict) else None,
            "proposal_source": candidate.get("proposal_source", "human") if isinstance(candidate, dict) else "human",
            "model_version": candidate.get("model_version") if isinstance(candidate, dict) else None,
        },
    }
    if isinstance(candidate, dict):
        if candidate.get("kind") == "numeric_max" and "limit" in candidate:
            record["requirement"]["limit"] = candidate["limit"]
        if candidate.get("kind") == "set_membership" and "approved_set" in candidate:
            record["requirement"]["approved_set"] = list(candidate["approved_set"])
    record["eligible_for_evaluation"] = state == "approved" and not issues
    return record


def requirement_for_engine(normalized: dict[str, Any]) -> dict[str, Any]:
    """Extract the engine requirement object only when approved and valid."""
    if not normalized.get("eligible_for_evaluation"):
        raise ValueError("requirement is not eligible for evaluation")
    return dict(normalized["requirement"])
