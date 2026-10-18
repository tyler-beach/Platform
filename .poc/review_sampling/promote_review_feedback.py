#!/usr/bin/env python3
"""Export adjudicated review events as evaluation-corpus candidates.

This tool never edits the baseline corpus and never promotes a case by itself.
Only explicitly approved, adjudicated events assigned to the training candidate
pool are exported. Holdout/evaluation splits are deliberately excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from review_events import read_events  # noqa: E402

LABELS = {"deviation", "no_deviation", "ambiguous"}
ALLOWED_ROUTES = {
    "applicability_retrieval",
    "collector_provenance",
    "evidence_retrieval",
    "inference_evaluation",
    "deterministic_guardrails",
    "exception_lifecycle",
    "runtime_evidence",
    "policy_adjudication",
    "other",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def export_candidates(events: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    excluded = {"not_adjudicated": 0, "not_approved": 0, "holdout_or_eval_split": 0,
                "invalid_label": 0, "missing_route": 0, "missing_provenance": 0}
    seen = set()
    for event in events:
        if event.get("event_type") != "review.adjudicated":
            excluded["not_adjudicated"] += 1
            continue
        if event.get("adjudication_status") != "adjudicated":
            excluded["not_adjudicated"] += 1
            continue
        if event.get("promotion_status") != "approved":
            excluded["not_approved"] += 1
            continue
        # Fail closed: missing split metadata must never default into a training pool.
        split = event.get("evaluation_split")
        if split not in {"candidate_train", "candidate_validation"}:
            excluded["holdout_or_eval_split"] += 1
            continue
        required_provenance = ("unit_id", "analysis_run_id", "analysis_version", "timestamp",
                               "evidence_refs", "rationale_summary", "event_hash")
        if any(not event.get(field) for field in required_provenance) or not event.get("adjudicator_id"):
            excluded["missing_provenance"] += 1
            continue
        label = event.get("evaluation_label")
        if label not in LABELS:
            excluded["invalid_label"] += 1
            continue
        route = event.get("feedback_route", "other")
        if route not in ALLOWED_ROUTES:
            excluded["missing_route"] += 1
            continue
        source_event_id = event["event_id"]
        if source_event_id in seen:
            raise ValueError(f"duplicate source event ID: {source_event_id}")
        seen.add(source_event_id)
        candidate = {
            "candidate_schema_version": "pathfinder.evaluation-candidate.v1",
            "candidate_id": "candidate-" + hashlib.sha256(source_event_id.encode("utf-8")).hexdigest()[:20],
            "source_review_event_id": source_event_id,
            "unit_id": event["unit_id"],
            "analysis_run_id": event["analysis_run_id"],
            "analysis_version": event["analysis_version"],
            "adjudicator_id": event.get("adjudicator_id", event["actor_id"]),
            "adjudicated_at": event["timestamp"],
            "evaluation_label": label,
            "evaluation_split": split,
            "feedback_route": route,
            "evidence_refs": event["evidence_refs"],
            "rationale_summary": event["rationale_summary"],
            "promotion_state": "candidate_pending_corpus_review",
            "source_event_hash": event["event_hash"],
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: item["candidate_id"])
    payload = {
        "export_schema_version": "pathfinder.evaluation-candidate-export.v1",
        "candidate_count": len(candidates),
        "excluded_counts": excluded,
        "candidates": candidates,
        "guardrails": [
            "Export creates candidates only; it never changes the baseline evaluation corpus.",
            "Holdout/evaluation cases are excluded from tuning candidates.",
            "A candidate requires separate corpus review, stable scenario fixtures, and regression evaluation before promotion.",
            "Reviewer dispositions alone are not labels; only approved adjudication events are eligible.",
        ],
    }
    payload["export_fingerprint_sha256"] = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path, help="Hash-chained review-events JSONL ledger")
    parser.add_argument("--output", required=True, type=Path, help="Candidate export JSON path")
    args = parser.parse_args()
    events = read_events(args.ledger)
    result = export_candidates(events)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"candidates={result['candidate_count']} fingerprint={result['export_fingerprint_sha256']}")
    print("Baseline corpus unchanged; exported records are pending human corpus review.")


if __name__ == "__main__":
    main()
