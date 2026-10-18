#!/usr/bin/env python3
"""Evaluate a pinned evidence package against the multi-ADR typed catalog.

Outcomes remain per-requirement engine outcomes. Aggregate status uses:
  all_aligned | deviations_found | mixed | insufficient_coverage | not_applicable_only
where "mixed" covers the common product language of partial alignment
(some requirements aligned, others deviant or inconclusive).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import catalog
import engine
import package_collector


def _scope_match(row: dict[str, Any], package: dict[str, Any]) -> bool:
    scope = package.get("scope") or {}
    domains = scope.get("domains")
    if isinstance(domains, list) and domains:
        return row.get("domain") in domains
    # If the package does not constrain domains, all catalog rows are in scope.
    return True


def aggregate_status(outcomes: list[str]) -> str:
    counts = Counter(outcomes)
    applicable = [o for o in outcomes if o != "not_applicable"]
    if not outcomes:
        return "insufficient_coverage"
    if applicable and all(o == "no_deviation_found" for o in applicable):
        return "all_aligned"
    if not applicable and counts.get("not_applicable"):
        return "not_applicable_only"
    has_dev = "supported_deviation" in counts
    has_ok = "no_deviation_found" in counts
    has_inc = "inconclusive" in counts
    if has_dev and not has_ok and not has_inc:
        return "deviations_found"
    if has_dev or (has_ok and has_inc) or (has_dev and has_ok):
        return "mixed"
    if has_inc and not has_ok and not has_dev:
        return "insufficient_coverage"
    if has_ok:
        return "all_aligned"
    return "insufficient_coverage"


def evaluate_package(
    package: dict[str, Any],
    *,
    requirements: list[dict[str, Any]] | None = None,
    adr_status: str = "accepted",
) -> dict[str, Any]:
    reqs = requirements if requirements is not None else catalog.load_requirements()
    observations = package_collector.collect_package_observations(package)
    results: list[dict[str, Any]] = []
    for row in reqs:
        scope_match = _scope_match(row, package)
        engine_req = catalog.requirement_for_engine(row)
        decision = engine.evaluate(
            engine_req,
            observations,
            adr_status=adr_status,
            scope_match=scope_match,
        )
        results.append({
            "adr_id": row["adr_id"],
            "domain": row.get("domain"),
            "title": row.get("title"),
            "requirement_id": row["requirement_id"],
            "kind": row["kind"],
            "predicate": row["predicate"],
            "subject": row["subject"],
            "outcome": decision["outcome"],
            "relationship": decision["relationship"],
            "rationale": decision["rationale"],
            "accepted_evidence_ids": decision["accepted_evidence_ids"],
            "uncertainty": decision["uncertainty"],
            "result_sha256": decision["result_sha256"],
            "label_status": row.get("label_status", "synthetic_unadjudicated"),
        })
    outcomes = [item["outcome"] for item in results]
    counts = Counter(outcomes)
    report = {
        "schema_version": "pathfinder-package-evaluation-v1",
        "engine_version": engine.ENGINE_VERSION,
        "package_id": package.get("package_id", "unnamed"),
        "catalog_size": len(reqs),
        "observation_count": len(observations),
        "aggregate_status": aggregate_status(outcomes),
        "aggregate_meaning": {
            "all_aligned": "All in-scope requirements with sufficient evidence are aligned.",
            "deviations_found": "One or more in-scope requirements are supported deviations.",
            "mixed": "Partial alignment: some requirements aligned, others deviant and/or inconclusive.",
            "insufficient_coverage": "In-scope requirements lack sufficient evidence for confident results.",
            "not_applicable_only": "No catalog requirements were in scope for this package.",
        }[aggregate_status(outcomes)],
        "counts": {
            "supported_deviation": counts.get("supported_deviation", 0),
            "no_deviation_found": counts.get("no_deviation_found", 0),
            "inconclusive": counts.get("inconclusive", 0),
            "not_applicable": counts.get("not_applicable", 0),
        },
        "results": results,
    }
    report["report_sha256"] = engine.fingerprint({k: v for k, v in report.items() if k != "report_sha256"})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Path to pathfinder-evidence-package-v1 JSON")
    parser.add_argument("--domains", nargs="*", help="Override package scope domains")
    parser.add_argument("--out", type=Path, help="Write report JSON")
    args = parser.parse_args(argv)
    try:
        package = package_collector.load_package(args.package)
        if args.domains:
            package = dict(package)
            scope = dict(package.get("scope") or {})
            scope["domains"] = list(args.domains)
            package["scope"] = scope
        report = evaluate_package(package)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
