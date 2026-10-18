#!/usr/bin/env python3
"""Replay one change event through Pathfinder's offline scope/evidence baseline.

The output is deterministic for a pinned event, catalog and local rules version.
It is a review artifact, not an enforcement decision or a production connector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / ".poc" / "scope"
sys.path.insert(0, str(SCOPE))
from retrieval import load_jsonl  # noqa: E402
from run_scope import evaluate_event  # noqa: E402

DEFAULT_CATALOG = SCOPE / "adr_catalog.jsonl"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def replay(event: dict[str, Any], catalog: list[dict[str, Any]], catalog_hash: str) -> dict[str, Any]:
    required = ("repository", "service", "domain", "language", "change_summary")
    missing = [field for field in required if not event.get(field)]
    if missing:
        raise ValueError("event missing required fields: " + ", ".join(missing))
    observations = event.get("source_observations", [])
    diff_lines = event.get("diff_lines", [])
    if not observations and not diff_lines:
        raise ValueError("event needs source_observations or exact diff_lines; summaries alone are not evidence")
    for index, observation in enumerate(observations, start=1):
        if not observation.get("excerpt") or not observation.get("path"):
            raise ValueError(f"source_observations[{index - 1}] needs path and exact excerpt")
    result = evaluate_event(
        event, catalog, top_k=5, in_scope_threshold=0.28,
        review_threshold=0.14, backend="local",
    )
    evidence = []
    for match in result.get("adr_matches", []):
        for observation in match.get("source_observations", []):
            evidence.append({
                "adr_id": match["adr_id"],
                "evidence_id": observation["evidence_id"],
                "path": observation.get("path"),
                "line": observation.get("line"),
                "excerpt_sha256": observation.get("excerpt_sha256"),
                "relationship": next(
                    (link["relationship"] for link in match.get("matched_cue_evidence", [])
                     if link.get("evidence_id") == observation.get("evidence_id")),
                    "observed_not_decisive",
                ),
            })
    payload = {
        "schema_version": "pathfinder.replay-report.v1",
        "event_id": str(event.get("case_id", event.get("event_id", "manual-event"))),
        "input_sha256": sha256(canonical(event).encode("utf-8")),
        "catalog_sha256": catalog_hash,
        "analysis_configuration": {
            "backend": "local_lexical_baseline",
            "top_k": 5,
            "in_scope_threshold": 0.28,
            "review_threshold": 0.14,
            "comparison_rules": "scope-cue-rules-v1",
        },
        "outcome": result["comparison"]["overall_result"],
        "scope_disposition": result["scope"]["disposition"],
        "matched_adr_ids": [match["adr_id"] for match in result.get("adr_matches", [])],
        "evidence_refs": evidence,
        "result": result,
        "interpretation": (
            "Deterministic offline replay. Cue-based outcomes are provisional review candidates; "
            "uncertain is a valid result when evidence does not establish the requirement. "
            "No model, cloud service, repository checkout or runtime telemetry was queried."
        ),
    }
    payload["report_sha256"] = sha256(canonical(payload).encode("utf-8"))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-json", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-repeat", action="store_true",
                        help="evaluate twice and fail if the canonical report differs")
    args = parser.parse_args()
    event_path = args.event_json if args.event_json.is_absolute() else ROOT / args.event_json
    catalog_path = args.catalog if args.catalog.is_absolute() else ROOT / args.catalog
    event_bytes = event_path.read_bytes()
    event = json.loads(event_bytes)
    catalog_bytes = catalog_path.read_bytes()
    catalog = load_jsonl(catalog_path)
    first = replay(event, catalog, sha256(catalog_bytes))
    if args.verify_repeat:
        second = replay(event, catalog, sha256(catalog_bytes))
        if canonical(first) != canonical(second):
            raise SystemExit("replay is not deterministic for identical inputs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(first, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "event_id": first["event_id"],
        "outcome": first["outcome"],
        "matched_adr_ids": first["matched_adr_ids"],
        "input_sha256": first["input_sha256"],
        "catalog_sha256": first["catalog_sha256"],
        "report_sha256": first["report_sha256"],
        "output": str(args.output),
        "repeat_verified": args.verify_repeat,
    }, indent=2))


if __name__ == "__main__":
    main()
