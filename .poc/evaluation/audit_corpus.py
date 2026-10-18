#!/usr/bin/env python3
"""Structural audit for the labeled synthetic evaluation corpus.

This command checks corpus integrity and emits explicit readiness gaps. It does
not estimate production detector quality or claim that a holdout exists.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

LABELS = {"deviation", "no_deviation", "ambiguous"}
REQUIRED = {"case_id", "title", "gold_label", "has_normative", "behavior", "entry_status", "dispatch", "requirement", "observation", "diff_excerpt"}


def audit(path: Path) -> dict[str, Any]:
    cases = []
    errors: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(item, dict):
            errors.append(f"line {line_no}: expected an object")
            continue
        missing = sorted(REQUIRED - item.keys())
        if missing:
            errors.append(f"line {line_no}: missing fields: {', '.join(missing)}")
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"line {line_no}: case_id must be a non-empty string")
        if item.get("gold_label") not in LABELS:
            errors.append(f"line {line_no}: unsupported gold_label {item.get('gold_label')!r}")
        if not isinstance(item.get("has_normative"), bool):
            errors.append(f"line {line_no}: has_normative must be boolean")
        for field in ("title", "behavior", "entry_status", "dispatch", "requirement", "observation", "diff_excerpt"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"line {line_no}: {field} must be a non-empty string")
        cases.append(item)

    ids = [item.get("case_id") for item in cases if isinstance(item.get("case_id"), str)]
    duplicates = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    errors.extend(f"duplicate case_id: {case_id}" for case_id in duplicates)
    counts = Counter(item.get("gold_label", "invalid") for item in cases)
    total = len(cases)
    label_counts = {label: counts.get(label, 0) for label in sorted(LABELS)}
    gaps = []
    if total < 100:
        gaps.append(f"Corpus has {total} cases; at least 100 adjudicated, diverse cases are required before a quality gate is meaningful.")
    if any(label_counts[label] == 0 for label in LABELS):
        gaps.append("At least one expected outcome class is absent.")
    gaps.append("A separately stored, locked holdout has not been verified by this corpus audit.")
    gaps.append("Labels and scenario coverage require human adjudication; structural validity is not label validity.")
    return {
        "schema_version": "pathfinder.evaluation-corpus-audit.v1",
        "corpus_path": str(path),
        "case_count": total,
        "label_counts": label_counts,
        "duplicate_case_ids": duplicates,
        "structurally_valid": not errors,
        "errors": errors,
        "readiness_gaps": gaps,
        "interpretation": "Structural integrity only; this report does not establish detector accuracy or production readiness.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(".poc/evaluation/cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.input)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["structurally_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
