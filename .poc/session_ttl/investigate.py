#!/usr/bin/env python3
"""Deterministic, evidence-bound session TTL investigation vertical slice.

Synthetic/offline reference implementation. It evaluates normalized evidence;
it does not semantically extract requirements from arbitrary ADR prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

POLICY_VERSION = "session-ttl-policy-v1"
MAX_TTL_SECONDS = 600
NORMALIZATION_CONTRACT_VERSION = "session-ttl-normalized-input-v1"
RESULT_SCHEMA_VERSION = "session-ttl-investigation-v1"
TTL_PREDICATE = "session.ttl_seconds"
OUTCOMES = {"supported_deviation", "no_deviation_found", "not_applicable", "inconclusive"}


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
    for artifact_name, artifact in (("adr", adr), ("source", source)):
        if artifact["artifact_id"] == "":
            raise ValueError(f"{artifact_name}.artifact_id must not be empty")
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


def evaluate(applicable: bool, ttl_values: list[dict[str, Any]]) -> dict[str, str]:
    if not applicable:
        return {
            "outcome": "not_applicable",
            "relationship": "not_applicable",
            "rationale": "The ADR is not applicable to this source revision; no compliance conclusion is asserted.",
        }
    if not ttl_values:
        return {
            "outcome": "inconclusive",
            "relationship": "insufficient_evidence",
            "rationale": "No valid, pinned session TTL value is present in the supplied evidence.",
        }
    if len({item["value"] for item in ttl_values}) != 1:
        return {
            "outcome": "inconclusive",
            "relationship": "conflicting_evidence",
            "rationale": "Pinned evidence contains conflicting session TTL values.",
        }
    ttl = ttl_values[0]["value"]
    if ttl > MAX_TTL_SECONDS:
        return {
            "outcome": "supported_deviation",
            "relationship": "contradicts",
            "rationale": f"Observed session TTL is {ttl} seconds, exceeding the applicable maximum of {MAX_TTL_SECONDS} seconds.",
        }
    return {
        "outcome": "no_deviation_found",
        "relationship": "consistent_with",
        "rationale": f"Observed session TTL is {ttl} seconds, within the applicable maximum of {MAX_TTL_SECONDS} seconds.",
    }


def validate_result(result: Any) -> None:
    """Validate the result contract before computing its fingerprint."""
    if not isinstance(result, dict):
        raise ValueError("result must be an object")
    required = {
        "schema_version", "policy_version", "policy", "normalization_contract_version",
        "case_id", "inputs", "applicability", "outcome", "relationship", "rationale",
        "evidence_ids", "rejected_observations", "uncertainty",
    }
    missing = sorted(required - set(result))
    if missing:
        raise ValueError("result missing required field(s): " + ", ".join(missing))
    if result["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ValueError("unsupported result schema version")
    if result["policy_version"] != POLICY_VERSION:
        raise ValueError("unsupported policy version")
    if result["outcome"] not in OUTCOMES:
        raise ValueError("invalid result outcome")
    if not isinstance(result["relationship"], str) or not isinstance(result["rationale"], str):
        raise ValueError("result relationship and rationale must be strings")
    if not isinstance(result["inputs"], list) or not isinstance(result["evidence_ids"], list):
        raise ValueError("result inputs and evidence_ids must be lists")
    if any(not isinstance(item, str) for item in result["evidence_ids"]):
        raise ValueError("result evidence_ids must contain strings")
    if len(result["evidence_ids"]) != len(set(result["evidence_ids"])):
        raise ValueError("result evidence_ids must be unique")
    if not isinstance(result["rejected_observations"], list) or not isinstance(result["uncertainty"], list):
        raise ValueError("result rejected_observations and uncertainty must be lists")
    if not isinstance(result["applicability"], dict) or type(result["applicability"].get("applicable")) is not bool:
        raise ValueError("result applicability must contain a boolean applicable field")
    if result["outcome"] == "no_deviation_found" and not result["applicability"]["applicable"]:
        raise ValueError("non-applicable result cannot claim no deviation found")
    if result["outcome"] == "supported_deviation" and not result["applicability"]["applicable"]:
        raise ValueError("non-applicable result cannot claim a deviation")


def fingerprint_result(result: dict[str, Any]) -> dict[str, Any]:
    validate_result(result)
    fingerprinted = dict(result)
    fingerprinted["result_sha256"] = sha256(canonical(result).encode("utf-8"))
    return fingerprinted


def investigate(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate normalized, pinned evidence and return a deterministic result."""
    normalized, artifacts, evidence, requested_ids = validate_case(case)
    adr, source = artifacts["adr"], artifacts["source"]
    applicable = adr["status"] == "accepted" and normalized["scope_match"]
    ttl_values, rejected = resolve_ttl_observations(evidence, requested_ids, source)
    decision = evaluate(applicable, ttl_values)
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
