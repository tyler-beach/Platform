#!/usr/bin/env python3
"""Build a redacted paste→catalog evaluation snapshot for GitHub Pages demos.

Uses checked-in messy fixtures. Never embeds tech-spec/code bodies in the output.
Live evaluation remains on GitHub Issues + Actions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / ".poc" / "requirement_engine"
FIXTURES = ROOT / ".poc" / "issue_analyze" / "fixtures"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

import evaluate_package  # noqa: E402
import paste_extractor  # noqa: E402

SCHEMA = "pathfinder-paste-eval-demo-v1"


def build_snapshot() -> dict[str, Any]:
    tech = (FIXTURES / "real_paste_tech_spec.md").read_text(encoding="utf-8")
    go = (FIXTURES / "real_paste_session.go").read_text(encoding="utf-8")
    package = {
        "schema_version": "pathfinder-evidence-package-v1",
        "package_id": "pages-paste-eval-fixtures",
        "scope": {
            "domains": [
                "identity", "security", "reliability", "messaging",
                "api", "privacy", "supply-chain", "observability", "cicd",
            ]
        },
        "tech_spec": {
            "artifact_id": "tech_spec",
            "path": "fixtures/real_paste_tech_spec.md",
            "content": tech,
        },
        "code": [{
            "artifact_id": "code-0",
            "path": "fixtures/real_paste_session.go",
            "content": go,
        }],
        "observations": [],
    }
    package = paste_extractor.ensure_observations(package)
    report = evaluate_package.evaluate_package(package)
    extracted = [
        {
            "predicate": item["predicate"],
            "subject": item["subject"],
            "value": item["value"],
            "locator_kind": (item.get("locator") or {}).get("kind"),
            "path": item.get("path"),
        }
        for item in package.get("observations") or []
    ]
    notable = [
        {
            "adr_id": row["adr_id"],
            "domain": row.get("domain"),
            "predicate": row["predicate"],
            "outcome": row["outcome"],
        }
        for row in report["results"]
        if row["outcome"] in {"supported_deviation", "no_deviation_found"}
    ][:20]
    snapshot = {
        "schema_version": SCHEMA,
        "synthetic": True,
        "label_status": "synthetic_unadjudicated",
        "backbone": "github-issues-actions",
        "package_id": package["package_id"],
        "fixtures": [
            "real_paste_tech_spec.md",
            "real_paste_session.go",
        ],
        "extractor": package.get("extraction") or {
            "extractor": paste_extractor.EXTRACTOR_ID,
            "extractor_version": paste_extractor.EXTRACTOR_VERSION,
            "observation_count": len(extracted),
        },
        "observation_count": report["observation_count"],
        "extracted_observations": extracted,
        "aggregate_status": report["aggregate_status"],
        "aggregate_meaning": report["aggregate_meaning"],
        "counts": report["counts"],
        "catalog_size": report["catalog_size"],
        "report_sha256": report["report_sha256"],
        "notable_results": notable,
        "issue_template": "pathfinder-analyze.yml",
        "workflow": "pathfinder-issue-analyze.yml",
        "docs_path": "docs/ISSUE_ANALYZE_WORKFLOW.md",
        "boundaries": [
            "Pages shows a redacted fixture snapshot only.",
            "Live paste evaluation runs on GitHub Issues and Actions.",
            "Full tech-spec/code bodies are never embedded in this snapshot.",
            "Unextracted predicates remain inconclusive.",
        ],
    }
    encoded = json.dumps(snapshot, sort_keys=True)
    for forbidden in (tech, go, "sk-live-checkout", "Sessions expire after 12 minutes"):
        if forbidden and forbidden in encoded:
            raise SystemExit("refusing to publish snapshot that embeds source content")
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = build_snapshot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(args.output),
        "aggregate_status": snapshot["aggregate_status"],
        "observation_count": snapshot["observation_count"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
