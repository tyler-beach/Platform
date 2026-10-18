"""Generic deterministic evaluator for normalized ADR requirements.

This is an offline reference engine. It consumes normalized, provenance-bound
observations; it does not parse arbitrary ADR prose or collect repository evidence.
Handlers branch on requirement kind, never on ADR identifiers.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

ENGINE_VERSION = "generic-requirement-engine-v3"
RESULT_SCHEMA_VERSION = "adr-requirement-result-v1"
KINDS = {
    "numeric_max",
    "numeric_min",
    "resource_present",
    "boolean_required",
    "set_membership",
    "dependency_forbidden",
}
OUTCOMES = {"supported_deviation", "no_deviation_found", "not_applicable", "inconclusive"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_requirement(requirement: Any) -> str:
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be an object")
    for field in ("requirement_id", "kind", "predicate", "subject"):
        if not _nonempty_string(requirement.get(field)):
            raise ValueError(f"requirement.{field} must be a non-empty string")
    kind = requirement["kind"]
    if kind not in KINDS:
        raise ValueError("unsupported requirement kind")
    if kind in {"numeric_max", "numeric_min"}:
        if type(requirement.get("limit")) not in (int, float) or isinstance(requirement.get("limit"), bool) or requirement["limit"] < 0:
            raise ValueError(f"{kind} requires a non-negative numeric limit")
    if kind in {"resource_present", "boolean_required", "dependency_forbidden"} and "limit" in requirement:
        raise ValueError(f"{kind} does not accept a limit")
    if kind == "set_membership":
        approved = requirement.get("approved_set")
        if not isinstance(approved, list) or not approved or any(not _nonempty_string(item) for item in approved):
            raise ValueError("set_membership requires a non-empty approved_set of strings")
        if "limit" in requirement:
            raise ValueError("set_membership does not accept a limit")
    return kind


def _value_valid(kind: str, value: Any) -> bool:
    if kind in {"numeric_max", "numeric_min"}:
        return type(value) in (int, float) and not isinstance(value, bool) and value >= 0
    if kind in {"resource_present", "boolean_required", "dependency_forbidden"}:
        return type(value) is bool
    if kind == "set_membership":
        return _nonempty_string(value)
    return False


def _deviates(kind: str, requirement: dict[str, Any], value: Any) -> bool:
    if kind == "numeric_max":
        return value > requirement["limit"]
    if kind == "numeric_min":
        return value < requirement["limit"]
    if kind in {"resource_present", "boolean_required"}:
        return value is False
    if kind == "dependency_forbidden":
        # true means the forbidden relationship/pattern is present
        return value is True
    if kind == "set_membership":
        return value not in requirement["approved_set"]
    raise ValueError("unsupported requirement kind")


def evaluate(requirement: Any, observations: Any, *, adr_status: str, scope_match: bool) -> dict[str, Any]:
    """Evaluate a typed requirement against normalized evidence conservatively."""
    kind = _validate_requirement(requirement)
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    if not _nonempty_string(adr_status) or type(scope_match) is not bool:
        raise ValueError("ADR status and scope_match are required and typed")

    evidence_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(observations):
        if not isinstance(item, dict):
            raise ValueError(f"observations[{index}] must be an object")
        for field in ("evidence_id", "predicate", "subject", "artifact_id", "revision", "path"):
            if not _nonempty_string(item.get(field)):
                raise ValueError(f"observations[{index}].{field} must be a non-empty string")
        if item["evidence_id"] in evidence_by_id:
            raise ValueError("evidence IDs must be unique")
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("source_sha256", ""))):
            raise ValueError(f"observations[{index}].source_sha256 must be a lowercase SHA-256 digest")
        locator = item.get("locator")
        if not isinstance(locator, dict) or not _nonempty_string(locator.get("kind")):
            raise ValueError(f"observations[{index}].locator must be typed")
        evidence_by_id[item["evidence_id"]] = item

    applicable = adr_status == "accepted" and scope_match
    matching = sorted(
        (item for item in observations
         if item["predicate"] == requirement["predicate"] and item["subject"] == requirement["subject"]),
        key=lambda item: item["evidence_id"],
    )
    accepted_ids: list[str] = []
    rejected_ids: list[str] = []
    uncertainty: list[str] = []
    if not applicable:
        outcome, relationship = "not_applicable", "not_applicable"
        rationale = "The ADR is not applicable; no compliance conclusion is asserted."
        matching = []
    elif not matching:
        outcome, relationship = "inconclusive", "insufficient_evidence"
        rationale = "No matching, provenance-bound observation was supplied."
        uncertainty = ["missing_observation"]
    else:
        values = [item.get("value") for item in matching]
        valid_flags = [_value_valid(kind, value) for value in values]
        if not all(valid_flags):
            outcome, relationship = "inconclusive", "invalid_observation"
            rationale = "At least one matching observation has an invalid value type or range."
            rejected_ids = [item["evidence_id"] for item, ok in zip(matching, valid_flags) if not ok]
            uncertainty = ["invalid_observation"]
        elif any(value != values[0] for value in values[1:]):
            outcome, relationship = "inconclusive", "conflicting_evidence"
            rationale = "Matching observations disagree; no single compliance conclusion is asserted."
            uncertainty = ["conflicting_observations"]
        else:
            accepted_ids = [item["evidence_id"] for item in matching]
            value = values[0]
            if _deviates(kind, requirement, value):
                outcome, relationship = "supported_deviation", "contradicts"
                rationale = "The normalized observation violates the typed requirement."
            else:
                outcome, relationship = "no_deviation_found", "consistent_with"
                rationale = "The normalized observation satisfies the typed requirement."

    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "requirement": dict(requirement),
        "applicability": {"applicable": applicable, "adr_status": adr_status, "scope_match": scope_match},
        "outcome": outcome,
        "relationship": relationship,
        "rationale": rationale,
        "considered_evidence_ids": [item["evidence_id"] for item in matching],
        "accepted_evidence_ids": accepted_ids,
        "rejected_evidence_ids": rejected_ids,
        "uncertainty": uncertainty,
        "provenance": [
            {key: item[key] for key in ("evidence_id", "artifact_id", "revision", "path", "source_sha256", "locator")}
            for item in matching
        ],
    }
    result["result_sha256"] = fingerprint(result)
    return result
