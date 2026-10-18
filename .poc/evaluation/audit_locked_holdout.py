#!/usr/bin/env python3
"""Fail-closed integrity check for Pathfinder's quarantined holdout seed set.

This checks lock integrity and separation only. It deliberately does not score
or expose labels; the current holdout is pending independent adjudication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = ROOT / ".poc" / "evaluation" / "holdout-lock.json"
LABEL_KEYS = {"gold_label", "label", "expected_outcome", "gold_comparison", "gold_disposition"}


def audit(lock_path: Path = DEFAULT_LOCK) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    dataset_path = ROOT / lock["dataset_path"]
    raw = dataset_path.read_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    errors: list[str] = []
    if actual_hash != lock.get("sha256"):
        errors.append("holdout fingerprint mismatch; do not use or overwrite this corpus")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    ids = [row.get("case_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate holdout case IDs")
    if sorted(ids) != sorted(lock.get("case_ids", [])):
        errors.append("holdout case IDs differ from the lock manifest")
    for row in rows:
        if LABEL_KEYS.intersection(row):
            errors.append(f"{row.get('case_id')}: holdout must not contain model-facing gold labels")
        if row.get("gold_label_status") != "pending_independent_adjudication":
            errors.append(f"{row.get('case_id')}: case is not marked pending independent adjudication")
        adjudication = row.get("adjudication", {})
        if adjudication.get("status") != "pending" or adjudication.get("reviewer_ids"):
            errors.append(f"{row.get('case_id')}: adjudication must remain pending with no reviewer IDs")
        event = row.get("event", {})
        if not event.get("source_observations") and not event.get("diff_lines"):
            errors.append(f"{row.get('case_id')}: no source-backed evidence")
    if lock.get("labels_are_ground_truth") is not False:
        errors.append("lock manifest must explicitly deny ground-truth status")
    if lock.get("status") != "quarantined_pending_independent_adjudication":
        errors.append("unexpected holdout status")
    return {
        "schema_version": "pathfinder.holdout-audit.v1",
        "structurally_valid": not errors,
        "case_count": len(rows),
        "case_ids": ids,
        "sha256": actual_hash,
        "status": lock.get("status"),
        "labels_are_ground_truth": lock.get("labels_are_ground_truth"),
        "errors": errors,
        "interpretation": (
            "Integrity and quarantine checks only. This corpus is not an accuracy benchmark "
            "until independent reviewers adjudicate labels and an approved evaluation procedure unlocks scoring."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.lock)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not result["structurally_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
