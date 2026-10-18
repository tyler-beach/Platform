#!/usr/bin/env python3
"""Compare two Pathfinder evaluation JSON reports without inventing release thresholds.

A comparison is only like-for-like when dataset fingerprints and analysis
configuration match. Changed corpora/configurations are reported explicitly;
the command never unlocks the holdout or changes a baseline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

METRICS = (
    "exact_three_way_accuracy",
    "clear_case_decision_coverage",
    "ambiguous_case_escalation_rate",
)
COUNT_METRICS = ("case_count", "three_way_correct", "clear_case_count", "ambiguous_case_count")


def load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("metrics"), dict):
        raise ValueError(f"{path}: expected evaluation JSON with a metrics object")
    if not isinstance(payload.get("dataset_fingerprint_sha256"), str):
        raise ValueError(f"{path}: missing dataset_fingerprint_sha256")
    if not isinstance(payload.get("analysis_configuration"), dict):
        raise ValueError(f"{path}: missing analysis_configuration")
    return payload


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_config = baseline["analysis_configuration"]
    candidate_config = candidate["analysis_configuration"]
    same_dataset = baseline["dataset_fingerprint_sha256"] == candidate["dataset_fingerprint_sha256"]
    same_config = baseline_config == candidate_config
    base_metrics, next_metrics = baseline["metrics"], candidate["metrics"]
    metric_deltas: dict[str, Any] = {}
    for key in METRICS:
        before, after = base_metrics.get(key), next_metrics.get(key)
        metric_deltas[key] = {
            "baseline": before,
            "candidate": after,
            "delta": (after - before) if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None,
        }
    counts = {
        key: {"baseline": base_metrics.get(key), "candidate": next_metrics.get(key)}
        for key in COUNT_METRICS
    }
    baseline_families = base_metrics.get("by_behavior", {})
    candidate_families = next_metrics.get("by_behavior", {})
    families = {}
    for family in sorted(set(baseline_families) | set(candidate_families)):
        before, after = baseline_families.get(family), candidate_families.get(family)
        families[family] = {
            "baseline": before,
            "candidate": after,
            "added": before is None,
            "removed": after is None,
        }
    return {
        "schema_version": "pathfinder.evaluation-comparison.v1",
        "comparison_status": "like_for_like" if same_dataset and same_config else "not_like_for_like",
        "same_dataset": same_dataset,
        "same_analysis_configuration": same_config,
        "baseline_fingerprint": baseline["dataset_fingerprint_sha256"],
        "candidate_fingerprint": candidate["dataset_fingerprint_sha256"],
        "baseline_configuration": baseline_config,
        "candidate_configuration": candidate_config,
        "metric_deltas": metric_deltas,
        "case_counts": counts,
        "scenario_families": families,
        "guardrails": [
            "No release threshold is applied; owners must approve thresholds against representative, independently adjudicated data.",
            "Metrics from different dataset fingerprints or analysis configurations are not like-for-like.",
            "Synthetic development labels are not ground truth and do not establish production quality.",
            "The locked holdout is excluded from this comparison and must never be used for tuning.",
            "Evidence support scores are not calibrated probabilities.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(load_report(args.baseline), load_report(args.candidate))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "comparison_status": result["comparison_status"],
        "same_dataset": result["same_dataset"],
        "same_analysis_configuration": result["same_analysis_configuration"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
