#!/usr/bin/env python3
"""Session TTL investigation adapter over the shared requirement engine.

Synthetic/offline reference implementation. Case validation and the TTL result
contract remain here for replay compatibility. Deviation decisions are produced
by engine.evaluate(kind=numeric_max), not an ADR-specific comparator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ENGINE_DIR = Path(__file__).resolve().parents[1] / "requirement_engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import engine  # noqa: E402
import predicate_registry  # noqa: E402

POLICY_VERSION = "session-ttl-policy-v1"
MAX_TTL_SECONDS = 600
NORMALIZATION_CONTRACT_VERSION = "session-ttl-normalized-input-v1"
RESULT_SCHEMA_VERSION = "session-ttl-investigation-v1"
TTL_PREDICATE = "session.ttl_seconds"
TTL_SUBJECT = "session"
OUTCOMES = {"supported_deviation", "no_deviation_found", "not_applicable", "inconclusive"}
TTL_REQUIREMENT = {
    "requirement_id": "ADR-TTL-001",
    "kind": "numeric_max",
    "predicate": TTL_PREDICATE,
    "subject": TTL_SUBJECT,
    "limit": MAX_TTL_SECONDS,
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_case(path: Path) -> dict[str, Any]:
    """Load JSON while rejecting duplicate keys that could make evidence ambiguous."""
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )


def validate_pinned_artifact(artifact: Any, label: str) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        raise ValueError(f"{label} must be an object")
    for field in ("artifact_id", "revision", "path", "content", "sha256"):
        if not isinstance(artifact.get(field), str) or not artifact[field].strip():
            raise ValueError(f"{label} requires non-empty string {field}")
    if not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
        raise ValueError(f"{label} sha256 must be a lowercase 64-character SHA-256 digest")
    expected = sha256(artifact["content"].encode("utf-8"))
    if artifact["sha256"] != expected:
        raise ValueError(f"{label} content hash does not match pinned sha256")
    return artifact


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer against a decoded JSON value."""
    if not isinstance(pointer, str):
        raise ValueError("JSON Pointer must be a string")
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must be empty or begin with '/'")
    value = document
    for raw_token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw_token):
            raise ValueError("invalid JSON Pointer escape")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if token not in value:
                raise ValueError("JSON Pointer object member does not exist")
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("JSON Pointer array index is not canonical")
            index = int(token)
            if index >= len(value):
                raise ValueError("JSON Pointer array index is out of range")
            value = value[index]
        else:
            raise ValueError("JSON Pointer traverses a scalar value")
    return value


def validate_evidence(case: dict[str, Any], adr: dict[str, Any], source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    evidence = case.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError(f"evidence[{index}] requires a non-empty evidence_id")
        if evidence_id in by_id:
            raise ValueError("evidence IDs must be unique")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ValueError(f"evidence {evidence_id} artifact_id must be a string")
        if artifact_id not in {adr["artifact_id"], source["artifact_id"]}:
            raise ValueError(f"evidence {evidence_id} points outside the pinned artifacts")
        expected_revision = adr["revision"] if artifact_id == adr["artifact_id"] else source["revision"]
        if item.get("revision") != expected_revision:
            raise ValueError(f"evidence {evidence_id} points to a stale artifact revision")
        locator = item.get("locator")
        if not isinstance(locator, dict) or not isinstance(locator.get("kind"), str) or not locator["kind"].strip():
            raise ValueError(f"evidence {evidence_id} requires a typed locator")
        if item.get("predicate") == TTL_PREDICATE and artifact_id == source["artifact_id"]:
            if locator["kind"] != "json_pointer":
                raise ValueError(f"evidence {evidence_id} uses an unsupported locator for session TTL")
            pointer = locator.get("pointer", locator.get("value"))
            try:
                document = json.loads(source["content"], object_pairs_hook=_reject_duplicate_json_keys)
                resolved = resolve_json_pointer(document, pointer)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                raise ValueError(f"evidence {evidence_id} JSON Pointer does not resolve in pinned source: {exc}") from exc
            claimed = item.get("value")
            if type(resolved) is not type(claimed) or resolved != claimed:
                raise ValueError(f"evidence {evidence_id} value does not match pinned source locator")
        by_id[evidence_id] = item

    requested = case.get("proposed_evidence_ids", list(by_id))
    if not isinstance(requested, list) or any(not isinstance(item, str) for item in requested):
        raise ValueError("proposed_evidence_ids must be a list of strings")
    if len(requested) != len(set(requested)):
        raise ValueError("proposed_evidence_ids must be unique")
    unknown = sorted(set(requested) - set(by_id))
    if unknown:
        raise ValueError("unknown evidence reference(s): " + ", ".join(unknown))
    return evidence, requested


def validate_case(case: Any) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str]]:
    if not isinstance(case, dict):
        raise ValueError("case must be a JSON object")
    adr = validate_pinned_artifact(case.get("adr"), "adr")
    source = validate_pinned_artifact(case.get("source"), "source")
    if adr["artifact_id"] == source["artifact_id"]:
        raise ValueError("ADR and source artifact IDs must be distinct")
    if not isinstance(adr.get("status"), str) or not adr["status"].strip():
        raise ValueError("adr.status must be a non-empty string")
    if type(case.get("scope_match")) is not bool:
        raise ValueError("scope_match must be a boolean")
    case_id = case.get("case_id", "unnamed")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id must be a non-empty string when supplied")
    supplied_limit = case.get("max_ttl_seconds", MAX_TTL_SECONDS)
    if type(supplied_limit) is not int or supplied_limit != MAX_TTL_SECONDS:
        raise ValueError(f"max_ttl_seconds must equal the {MAX_TTL_SECONDS}-second limit in {POLICY_VERSION}")
    try:
        json.loads(source["content"], object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("source content must be valid JSON") from exc
    evidence, requested = validate_evidence(case, adr, source)
    return {"case_id": case_id, "scope_match": case["scope_match"]}, {"adr": adr, "source": source}, evidence, requested


def resolve_ttl_observations(evidence: list[dict[str, Any]], requested_ids: list[str], source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    candidates = [
        item for item in evidence
        if item.get("predicate") == TTL_PREDICATE
        and item.get("artifact_id") == source["artifact_id"]
        and item.get("evidence_id") in requested_ids
    ]
    accepted = [
        item for item in candidates
        if type(item.get("value")) is int and item["value"] >= 0
    ]
    rejected: list[dict[str, str]] = []
    for item in candidates:
        value = item.get("value")
        if type(value) is not int:
            rejected.append({"evidence_id": item["evidence_id"], "reason_code": "unexpected_numeric_type"})
        elif value < 0:
            rejected.append({"evidence_id": item["evidence_id"], "reason_code": "negative_value"})
    return accepted, sorted(rejected, key=lambda item: item["evidence_id"])


def _engine_observations(ttl_values: list[dict[str, Any]], source: dict[str, Any]) -> list[dict[str, Any]]:
    """Map validated TTL evidence rows onto the shared engine observation contract."""
    predicate_registry.asserts_compatible("numeric_max", TTL_PREDICATE)
    observations: list[dict[str, Any]] = []
    for item in ttl_values:
        locator = item.get("locator") if isinstance(item.get("locator"), dict) else {"kind": "json_pointer"}
        observations.append({
            "evidence_id": item["evidence_id"],
            "predicate": TTL_PREDICATE,
            "subject": TTL_SUBJECT,
            "value": item["value"],
            "artifact_id": source["artifact_id"],
            "revision": source["revision"],
            "path": source["path"],
            "source_sha256": source["sha256"],
            "locator": locator if locator.get("kind") else {"kind": "json_pointer", "value": locator.get("value", "")},
        })
    return observations


def evaluate_with_engine(*, adr_status: str, scope_match: bool, ttl_values: list[dict[str, Any]], source: dict[str, Any]) -> dict[str, Any]:
    """Decide via shared engine; return engine outcome fields plus optional TTL rationale detail."""
    result = engine.evaluate(
        TTL_REQUIREMENT,
        _engine_observations(ttl_values, source),
        adr_status=adr_status,
        scope_match=scope_match,
    )
    decision = {
        "outcome": result["outcome"],
        "relationship": result["relationship"],
        "rationale": result["rationale"],
        "engine_version": result["engine_version"],
        "engine_result_sha256": result["result_sha256"],
    }
    if result["outcome"] in {"supported_deviation", "no_deviation_found"} and ttl_values:
        ttl = ttl_values[0]["value"]
        if result["outcome"] == "supported_deviation":
            decision["rationale"] = (
                f"Observed session TTL is {ttl} seconds, exceeding the applicable maximum of {MAX_TTL_SECONDS} seconds."
            )
        else:
            decision["rationale"] = (
                f"Observed session TTL is {ttl} seconds, within the applicable maximum of {MAX_TTL_SECONDS} seconds."
            )
    elif result["outcome"] == "not_applicable":
        decision["rationale"] = (
            "The ADR is not applicable to this source revision; no compliance conclusion is asserted."
        )
    elif result["relationship"] == "insufficient_evidence":
        decision["rationale"] = "No valid, pinned session TTL value is present in the supplied evidence."
    elif result["relationship"] == "conflicting_evidence":
        decision["rationale"] = "Pinned evidence contains conflicting session TTL values."
    return decision


def evaluate(applicable: bool, ttl_values: list[dict[str, Any]]) -> dict[str, str]:
    """Compatibility wrapper; prefer evaluate_with_engine from investigate()."""
    source = {"artifact_id": "compat", "revision": "compat", "path": "compat.json",
              "sha256": hashlib.sha256(b"compat").hexdigest()}
    decision = evaluate_with_engine(
        adr_status="accepted" if applicable else "proposed",
        scope_match=applicable,
        ttl_values=ttl_values,
        source=source,
    )
    return {key: decision[key] for key in ("outcome", "relationship", "rationale")}


def validate_result(result: Any) -> None:
    """Validate result shape and cross-field invariants before fingerprinting."""
    if not isinstance(result, dict):
        raise ValueError("result must be an object")
    required = {"schema_version", "policy_version", "policy", "normalization_contract_version", "case_id", "inputs", "applicability", "outcome", "relationship", "rationale", "evidence_ids", "considered_evidence_ids", "accepted_evidence_ids", "rejected_observations", "uncertainty"}
    missing = sorted(required - set(result))
    if missing:
        raise ValueError("result missing required field(s): " + ", ".join(missing))
    if result["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ValueError("unsupported result schema version")
    if result["policy_version"] != POLICY_VERSION:
        raise ValueError("unsupported policy version")
    outcome = result["outcome"]
    if not isinstance(outcome, str) or outcome not in OUTCOMES:
        raise ValueError("invalid result outcome")
    expected_policy = {"predicate": TTL_PREDICATE, "operator": "maximum", "limit_seconds": MAX_TTL_SECONDS}
    if result["policy"] != expected_policy:
        raise ValueError("result policy does not match pinned policy parameters")
    for field in ("normalization_contract_version", "case_id", "relationship", "rationale"):
        if not isinstance(result[field], str) or not result[field].strip():
            raise ValueError(f"result {field} must be a non-empty string")
    inputs = result["inputs"]
    if not isinstance(inputs, list) or len(inputs) != 2:
        raise ValueError("result inputs must contain ADR and source artifacts")
    artifact_ids = []
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise ValueError(f"result inputs[{index}] must be an object")
        for field in ("artifact_id", "revision", "path", "sha256"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"result inputs[{index}] requires non-empty {field}")
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError(f"result inputs[{index}] has invalid sha256")
        artifact_ids.append(item["artifact_id"])
    if len(set(artifact_ids)) != 2:
        raise ValueError("result input artifact IDs must be distinct")
    applicability = result["applicability"]
    if not isinstance(applicability, dict) or type(applicability.get("applicable")) is not bool:
        raise ValueError("result applicability must contain a boolean applicable field")
    if not isinstance(applicability.get("adr_status"), str) or type(applicability.get("scope_match")) is not bool:
        raise ValueError("result applicability status and scope fields are invalid")
    expected_applicable = applicability["adr_status"] == "accepted" and applicability["scope_match"]
    if applicability["applicable"] != expected_applicable:
        raise ValueError("result applicability fields are inconsistent")
    for field in ("evidence_ids", "considered_evidence_ids", "accepted_evidence_ids"):
        values = result[field]
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"result {field} must be a list of non-empty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"result {field} must be unique")
    evidence_ids = set(result["evidence_ids"])
    considered = set(result["considered_evidence_ids"])
    accepted = set(result["accepted_evidence_ids"])
    if evidence_ids != considered:
        raise ValueError("evidence_ids must equal considered_evidence_ids")
    rejected = result["rejected_observations"]
    if not isinstance(rejected, list):
        raise ValueError("result rejected_observations must be a list")
    rejected_ids = []
    allowed_reasons = {"negative_value", "unexpected_numeric_type"}
    for index, item in enumerate(rejected):
        if not isinstance(item, dict) or not isinstance(item.get("evidence_id"), str) or not item["evidence_id"]:
            raise ValueError(f"result rejected_observations[{index}] requires an evidence_id")
        reason = item.get("reason_code")
        if not isinstance(reason, str) or reason not in allowed_reasons:
            raise ValueError(f"result rejected_observations[{index}] has an unknown reason_code")
        rejected_ids.append(item["evidence_id"])
    if len(rejected_ids) != len(set(rejected_ids)):
        raise ValueError("rejected observation IDs must be unique")
    if not accepted.issubset(considered) or not set(rejected_ids).issubset(considered):
        raise ValueError("accepted and rejected evidence must be subsets of considered evidence")
    if accepted.intersection(rejected_ids):
        raise ValueError("evidence cannot be both accepted and rejected")
    uncertainty = result["uncertainty"]
    if not isinstance(uncertainty, list) or any(not isinstance(value, str) or not value for value in uncertainty):
        raise ValueError("result uncertainty must be a list of non-empty strings")
    if rejected and (outcome != "inconclusive" or result["relationship"] != "invalid_observation"):
        raise ValueError("rejected observations require inconclusive/invalid_observation result")
    if not applicability["applicable"]:
        if outcome != "not_applicable" or result["relationship"] != "not_applicable":
            raise ValueError("non-applicable result must use not_applicable outcome and relationship")
        if evidence_ids or accepted or rejected:
            raise ValueError("non-applicable result cannot claim decision evidence")
    elif outcome == "not_applicable":
        raise ValueError("applicable result cannot claim not_applicable")
    expected_relationship = {"supported_deviation": "contradicts", "no_deviation_found": "consistent_with", "not_applicable": "not_applicable", "inconclusive": {"insufficient_evidence", "conflicting_evidence", "invalid_observation"}}[outcome]
    if isinstance(expected_relationship, set):
        if result["relationship"] not in expected_relationship:
            raise ValueError("result relationship is inconsistent with outcome")
    elif result["relationship"] != expected_relationship:
        raise ValueError("result relationship is inconsistent with outcome")
    if outcome in {"supported_deviation", "no_deviation_found"} and not accepted:
        raise ValueError("confident result requires accepted evidence")
    if outcome == "inconclusive" and not uncertainty:
        raise ValueError("inconclusive result requires uncertainty")
    if outcome != "inconclusive" and uncertainty:
        raise ValueError("conclusive result cannot carry uncertainty")

def fingerprint_result(result: dict[str, Any]) -> dict[str, Any]:
    validate_result(result)
    fingerprinted = dict(result)
    fingerprinted["result_sha256"] = sha256(canonical(result).encode("utf-8"))
    return fingerprinted


def investigate(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate normalized, pinned evidence via the shared engine and return a deterministic result."""
    normalized, artifacts, evidence, requested_ids = validate_case(case)
    adr, source = artifacts["adr"], artifacts["source"]
    applicable = adr["status"] == "accepted" and normalized["scope_match"]
    ttl_values, rejected = resolve_ttl_observations(evidence, requested_ids, source)
    decision = evaluate_with_engine(
        adr_status=adr["status"],
        scope_match=normalized["scope_match"],
        ttl_values=ttl_values,
        source=source,
    )
    decision.pop("engine_version", None)
    decision.pop("engine_result_sha256", None)
    if applicable and rejected:
        decision = {
            "outcome": "inconclusive",
            "relationship": "invalid_observation",
            "rationale": "At least one decision-relevant TTL observation was rejected; the available valid values are not sufficient to assert compliance or deviation.",
        }
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "policy": {"predicate": TTL_PREDICATE, "operator": "maximum", "limit_seconds": MAX_TTL_SECONDS},
        "normalization_contract_version": NORMALIZATION_CONTRACT_VERSION,
        "case_id": normalized["case_id"],
        "inputs": [
            {"artifact_id": item["artifact_id"], "revision": item["revision"], "path": item["path"], "sha256": item["sha256"]}
            for item in (adr, source)
        ],
        "applicability": {"applicable": applicable, "adr_status": adr["status"], "scope_match": normalized["scope_match"]},
        **decision,
        "evidence_ids": sorted(item["evidence_id"] for item in (
            [entry for entry in evidence if entry.get("predicate") == TTL_PREDICATE and entry.get("artifact_id") == source["artifact_id"] and entry.get("evidence_id") in requested_ids]
            if applicable else []
        )),
        "considered_evidence_ids": sorted(item["evidence_id"] for item in (
            [entry for entry in evidence if entry.get("predicate") == TTL_PREDICATE and entry.get("artifact_id") == source["artifact_id"] and entry.get("evidence_id") in requested_ids]
            if applicable else []
        )),
        "accepted_evidence_ids": sorted(item["evidence_id"] for item in (ttl_values if applicable else [])),
        "rejected_observations": rejected if applicable else [],
        "uncertainty": [] if decision["outcome"] != "inconclusive" else [decision["relationship"]],
    }
    return fingerprint_result(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to a synthetic normalized case JSON file")
    parser.add_argument("--output", type=Path, help="Write canonical result JSON to this path")
    parser.add_argument("--verify-repeat", action="store_true", help="Run twice and fail if result fingerprints differ")
    args = parser.parse_args(argv)
    try:
        case = load_case(args.case)
        result = investigate(case)
        if args.verify_repeat and result != investigate(load_case(args.case)):
            raise ValueError("deterministic replay mismatch")
        encoded = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
