#!/usr/bin/env python3
"""Validate the sampled-issue -> disposition -> adjudication -> candidate-export path.

This command reads the immutable review ledger and sample manifest, checks that
reviewed units came from the recorded sample, requires an earlier disposition
and a distinct adjudicator, then writes candidate artifacts. It never mutates
the labeled baseline or locked holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from promote_review_feedback import export_candidates  # noqa: E402
from review_events import read_events  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_sample_manifest(batch: dict[str, Any]) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    if not isinstance(batch.get("seed"), str) or not batch["seed"]:
        errors.append("sample manifest is missing its reproducible seed")
    frame = batch.get("frame")
    if not isinstance(frame, dict) or not isinstance(frame.get("fingerprint_sha256"), str) or len(frame["fingerprint_sha256"]) != 64:
        errors.append("sample manifest is missing its frame fingerprint")
    units: set[str] = set()
    for queue in ("probability_sample", "risk_sample"):
        rows = batch.get(queue, [])
        if not isinstance(rows, list):
            errors.append(f"{queue} must be a list")
            continue
        for item in rows:
            unit_id = item.get("unit_id") if isinstance(item, dict) else None
            if not isinstance(unit_id, str) or not unit_id:
                errors.append(f"{queue} contains an invalid unit_id")
                continue
            units.add(unit_id)
            if queue == "probability_sample":
                probability = item.get("inclusion_probability")
                weight = item.get("design_weight")
                if not isinstance(probability, (int, float)) or not 0 < probability <= 1:
                    errors.append(f"{unit_id}: probability sample requires a valid inclusion_probability")
                elif not isinstance(weight, (int, float)) or abs(weight - (1.0 / probability)) > 1e-8:
                    errors.append(f"{unit_id}: design_weight must be the reciprocal of inclusion_probability")
                if item.get("selection_reason") != "STRATIFIED_RANDOM":
                    errors.append(f"{unit_id}: probability sample has an unexpected selection reason")
            else:
                if item.get("population_inclusion_probability", "missing") is not None:
                    errors.append(f"{unit_id}: risk-only selection must not claim a population inclusion probability")
                if item.get("selection_reason") != "RISK_TRIAGE":
                    errors.append(f"{unit_id}: risk sample has an unexpected selection reason")
    return units, errors


def validate_cycle(events: list[dict[str, Any]], batch: dict[str, Any]) -> dict[str, Any]:
    selected, errors = validate_sample_manifest(batch)
    dispositions: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    adjudications: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(events):
        unit_id = event.get("unit_id")
        if unit_id not in selected:
            errors.append(f"{event.get('event_id')}: unit is not in the supplied sample manifest")
        if event.get("event_type") == "review.dispositioned":
            dispositions.setdefault(unit_id, []).append((index, event))
        elif event.get("event_type") == "review.adjudicated":
            adjudications.append((index, event))
    for index, event in adjudications:
        prior = [(position, item) for position, item in dispositions.get(event.get("unit_id"), []) if position < index]
        if not prior:
            errors.append(f"{event.get('event_id')}: adjudication has no earlier disposition for this unit")
            continue
        adjudicator = event.get("adjudicator_id")
        if not isinstance(adjudicator, str) or not adjudicator.strip() or not any(
            item.get("actor_id") != adjudicator for _, item in prior
        ):
            errors.append(f"{event.get('event_id')}: adjudicator must be identified and distinct from the disposition reviewer")
        if event.get("adjudication_status") != "adjudicated":
            errors.append(f"{event.get('event_id')}: adjudication status is not final")
    return {
        "schema_version": "pathfinder.feedback-cycle-audit.v1",
        "valid": not errors,
        "sample_seed": batch.get("seed"),
        "sample_frame_sha256": batch.get("frame", {}).get("fingerprint_sha256"),
        "sampled_unit_count": len(selected),
        "ledger_event_count": len(events),
        "disposition_event_count": sum(e.get("event_type") == "review.dispositioned" for e in events),
        "adjudication_event_count": len(adjudications),
        "errors": errors,
        "guardrails": [
            "GitHub Issues are intake, not the authoritative ledger.",
            "Candidate export is not baseline promotion.",
            "The labeled baseline and locked holdout are read-only inputs.",
            "Probability-sample estimates must not include risk-only units without valid inclusion probabilities.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--sample-batch", required=True, type=Path)
    parser.add_argument("--baseline-cases", type=Path, default=ROOT / ".poc" / "evaluation" / "cases.jsonl")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    baseline_before = sha256(args.baseline_cases)
    events = read_events(args.ledger)
    batch = json.loads(args.sample_batch.read_text(encoding="utf-8"))
    report = validate_cycle(events, batch)
    candidates = export_candidates(events) if report["valid"] else {
        "candidate_schema_version": "pathfinder.evaluation-candidates.v1",
        "candidate_count": 0, "candidates": [],
        "excluded_counts": {"cycle_validation_failed": 1},
    }
    baseline_after = sha256(args.baseline_cases)
    report["baseline_sha256_before"] = baseline_before
    report["baseline_sha256_after"] = baseline_after
    report["baseline_unchanged"] = baseline_before == baseline_after
    report["candidate_count"] = candidates.get("candidate_count", 0)
    if not report["baseline_unchanged"]:
        report["errors"].append("baseline corpus changed during feedback-cycle validation")
        report["valid"] = False
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "feedback-cycle-audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "candidate-export.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "valid": report["valid"], "sampled_unit_count": report["sampled_unit_count"],
        "ledger_event_count": report["ledger_event_count"],
        "candidate_count": report["candidate_count"],
        "baseline_unchanged": report["baseline_unchanged"],
        "output_dir": str(args.output_dir),
        "errors": report["errors"],
    }, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
