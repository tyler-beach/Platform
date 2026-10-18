#!/usr/bin/env python3
"""Deterministic, stratified review sampler for synthetic/offline assessment frames.

The probability sample estimates population quality. Risk triage is a separate
diagnostic queue and must not be mixed into weighted population estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

OUTCOMES = {"deviation", "no_deviation", "potential", "inconclusive"}
REQUIRED = {"unit_id", "outcome", "evidence_band"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_frame(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"line {index}: each assessment must be a JSON object")
        missing = REQUIRED - row.keys()
        if missing:
            raise ValueError(f"line {index}: missing fields: {', '.join(sorted(missing))}")
        unit_id = row["unit_id"]
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError(f"line {index}: unit_id must be a non-empty string")
        if unit_id in seen:
            raise ValueError(f"duplicate unit_id: {unit_id}")
        seen.add(unit_id)
        if row["outcome"] not in OUTCOMES:
            raise ValueError(f"{unit_id}: unsupported outcome {row['outcome']!r}")
        if not isinstance(row["evidence_band"], str) or not row["evidence_band"]:
            raise ValueError(f"{unit_id}: evidence_band must be a non-empty string")
        flags = row.get("risk_flags", [])
        if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
            raise ValueError(f"{unit_id}: risk_flags must be a list of strings")
    return rows


def rank(seed: str, unit_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{unit_id}".encode("utf-8")).hexdigest()


def build_batch(rows: list[dict[str, Any]], *, seed: str, per_stratum: int, policy_version: str = "review-sampling-v1") -> dict[str, Any]:
    if per_stratum < 1:
        raise ValueError("per_stratum must be >= 1")
    canonical_rows = sorted((canonical(row) for row in rows))
    frame_sha = hashlib.sha256("\n".join(canonical_rows).encode("utf-8")).hexdigest()
    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        strata[(row["outcome"], row["evidence_band"])].append(row)

    probability_sample = []
    stratum_summary = []
    for (outcome, band), members in sorted(strata.items()):
        ordered = sorted(members, key=lambda row: (rank(seed, row["unit_id"]), row["unit_id"]))
        chosen = ordered[: min(per_stratum, len(ordered))]
        probability = len(chosen) / len(members)
        stratum_summary.append({
            "outcome": outcome, "evidence_band": band,
            "population_count": len(members), "selected_count": len(chosen),
            "inclusion_probability": round(probability, 12),
        })
        for row in chosen:
            probability_sample.append({
                "unit_id": row["unit_id"], "outcome": outcome,
                "evidence_band": band, "stratum_population_count": len(members),
                "inclusion_probability": round(probability, 12),
                "design_weight": round(1.0 / probability, 12),
                "selection_reason": "STRATIFIED_RANDOM",
            })

    risk_sample = []
    for row in sorted(rows, key=lambda item: item["unit_id"]):
        flags = sorted(set(row.get("risk_flags", [])))
        if str(row.get("impact", "")).lower() in {"critical", "high"}:
            flags.append("HIGH_IMPACT")
        flags = sorted(set(flags))
        if flags:
            risk_sample.append({
                "unit_id": row["unit_id"], "outcome": row["outcome"],
                "evidence_band": row["evidence_band"],
                "selection_reason": "RISK_TRIAGE", "risk_flags": flags,
                "population_inclusion_probability": None,
                "note": "Diagnostic queue; not representative and excluded from probability-sample estimates.",
            })

    return {
        "schema_version": "pathfinder.review-sample-batch.v1",
        "policy_version": policy_version,
        "seed": seed,
        "frame": {
            "fingerprint_sha256": frame_sha, "unit_count": len(rows),
            "strata_count": len(strata), "unit": "requirement x artifact snapshot x analysis run",
        },
        "strata": stratum_summary,
        "probability_sample": sorted(probability_sample, key=lambda item: item["unit_id"]),
        "risk_sample": risk_sample,
        "guardrails": [
            "Probability and risk samples are separate; do not combine unweighted.",
            "Inclusion probabilities apply only to the supplied immutable frame and this policy.",
            "Evidence-strength scores are not correctness probabilities.",
            "This offline prototype assigns no reviewers and persists no review dispositions.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSONL assessment frame")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON batch manifest")
    parser.add_argument("--seed", required=True, help="Reproducible sampling seed")
    parser.add_argument("--per-stratum", type=int, default=2, help="Maximum random selections per outcome/evidence-band stratum")
    args = parser.parse_args()
    batch = build_batch(load_frame(args.input), seed=args.seed, per_stratum=args.per_stratum)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"frame={batch['frame']['fingerprint_sha256']} units={batch['frame']['unit_count']} probability_sample={len(batch['probability_sample'])} risk_sample={len(batch['risk_sample'])}")


if __name__ == "__main__":
    main()
