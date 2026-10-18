#!/usr/bin/env python3
"""Deterministic, evidence-bound session TTL investigation vertical slice.

This is a synthetic offline reference implementation. It deliberately performs
applicability and numeric validation without an LLM; semantic extraction and
production source adapters are separate concerns.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

POLICY_VERSION = "session-ttl-policy-v1"
PARSER_VERSION = "explicit-ttl-fixture-v1"
OUTCOMES = {"supported_deviation", "no_deviation_found", "inconclusive"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_pinned_artifact(artifact: dict[str, Any], label: str) -> None:
    for field in ("artifact_id", "revision", "path", "content"):
        if not isinstance(artifact.get(field), str) or not artifact[field].strip():
            raise ValueError(f"{label} requires non-empty {field}")
    expected = sha256(artifact["content"].encode("utf-8"))
    if artifact.get("sha256") != expected:
        raise ValueError(f"{label} content hash does not match pinned sha256")


def investigate(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a normalized, pinned fixture and return a deterministic result."""
    adr = case.get("adr")
    source = case.get("source")
    if not isinstance(adr, dict) or not isinstance(source, dict):
        raise ValueError("case requires adr and source objects")
    validate_pinned_artifact(adr, "adr")
    validate_pinned_artifact(source, "source")

    evidence = case.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("evidence_id"), str) or not item["evidence_id"]:
            raise ValueError("each evidence item requires a non-empty evidence_id")
        if item["evidence_id"] in evidence_by_id:
            raise ValueError("evidence IDs must be unique")
        if item.get("artifact_id") not in {adr["artifact_id"], source["artifact_id"]}:
            raise ValueError(f"evidence {item['evidence_id']} points outside the pinned artifacts")
        if item.get("revision") != (adr["revision"] if item["artifact_id"] == adr["artifact_id"] else source["revision"]):
            raise ValueError(f"evidence {item['evidence_id']} points to a stale artifact revision")
        if not isinstance(item.get("locator"), dict) or not item["locator"].get("kind"):
            raise ValueError(f"evidence {item['evidence_id']} requires a typed locator")

    requested_ids = case.get("proposed_evidence_ids", [item["evidence_id"] for item in evidence])
    if not isinstance(requested_ids, list) or any(not isinstance(x, str) for x in requested_ids):
        raise ValueError("proposed_evidence_ids must be a list of strings")
    unknown = sorted(set(requested_ids) - set(evidence_by_id))
    if unknown:
        raise ValueError("unknown evidence reference(s): " + ", ".join(unknown))

    # Applicability is deliberately evaluated before examining the TTL observation.
    applicability = adr.get("status") == "accepted" and case.get("scope_match") is True
    ttl_values = [
        item for item in evidence
        if item.get("predicate") == "session.ttl_seconds"
        and item.get("artifact_id") == source["artifact_id"]
        and item.get("evidence_id") in requested_ids
        and isinstance(item.get("value"), int)
        and not isinstance(item.get("value"), bool)
        and item["value"] >= 0
    ]
    rationale: str
    if not applicability:
        outcome = "no_deviation_found"
        rationale = "The ADR is not applicable to this source revision; no deviation is asserted."
        relation = "not_applicable"
    elif not ttl_values:
        outcome = "inconclusive"
        rationale = "No valid, pinned session TTL value is present in the supplied evidence."
        relation = "insufficient_evidence"
    elif len({item["value"] for item in ttl_values}) != 1:
        outcome = "inconclusive"
        rationale = "Pinned evidence contains conflicting session TTL values."
        relation = "conflicting_evidence"
    else:
        ttl = ttl_values[0]["value"]
        limit = case.get("max_ttl_seconds", 600)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("max_ttl_seconds must be a non-negative integer")
        if ttl > limit:
            outcome = "supported_deviation"
            rationale = f"Observed session TTL is {ttl} seconds, exceeding the applicable maximum of {limit} seconds."
            relation = "contradicts"
        else:
            outcome = "no_deviation_found"
            rationale = f"Observed session TTL is {ttl} seconds, within the applicable maximum of {limit} seconds."
            relation = "consistent_with"

    result = {
        "schema_version": "session-ttl-investigation-v1",
        "policy_version": POLICY_VERSION,
        "parser_version": PARSER_VERSION,
        "case_id": case.get("case_id", "unnamed"),
        "inputs": [
            {"artifact_id": artifact["artifact_id"], "revision": artifact["revision"], "path": artifact["path"], "sha256": artifact["sha256"]}
            for artifact in (adr, source)
        ],
        "applicability": {"applicable": applicability, "adr_status": adr.get("status"), "scope_match": case.get("scope_match")},
        "outcome": outcome,
        "relationship": relation,
        "rationale": rationale,
        "evidence_ids": sorted(requested_ids),
        "uncertainty": [] if outcome != "inconclusive" else [relation],
    }
    result["result_sha256"] = sha256(canonical(result).encode("utf-8"))
    return result


def load_case(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to a synthetic normalized case JSON file")
    parser.add_argument("--output", type=Path, help="Write canonical result JSON to this path")
    parser.add_argument("--verify-repeat", action="store_true", help="Run twice and fail if result fingerprints differ")
    args = parser.parse_args()
    case = load_case(args.case)
    result = investigate(case)
    if args.verify_repeat and result != investigate(load_case(args.case)):
        raise SystemExit("deterministic replay mismatch")
    encoded = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
