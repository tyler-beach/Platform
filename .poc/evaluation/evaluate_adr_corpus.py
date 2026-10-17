#!/usr/bin/env python3
"""Audit the synthetic natural-language ADR corpus and its source fixtures.

This checks corpus integrity and deterministic evidence collection. It does not
invoke a model or claim that labels are independently adjudicated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / ".poc" / "evaluation" / "adr-corpus"
MANIFEST = CORPUS / "manifest.jsonl"

import sys
sys.path.insert(0, str(ROOT / ".poc"))
import observations


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases() -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("ADR corpus case IDs must be unique")
    return cases


def validate_case(case: dict[str, Any]) -> tuple[Path, Path]:
    required = {"case_id", "domain", "adr_path", "adr_sha256", "requirement_excerpt", "expected_outcome", "expected_relation", "source_capability", "fixture_path", "fixture_sha256", "expected_fact"}
    missing = required - set(case)
    if missing:
        raise ValueError(f"{case.get('case_id', '<unknown>')}: missing fields {sorted(missing)}")
    if case["expected_outcome"] not in {"deviation", "no_deviation", "inconclusive"}:
        raise ValueError(f"{case['case_id']}: invalid expected_outcome")
    expected_relation = {"deviation": "contradicts", "no_deviation": "consistent_with", "inconclusive": "uncertain"}[case["expected_outcome"]]
    if case["expected_relation"] != expected_relation:
        raise ValueError(f"{case['case_id']}: expected_relation conflicts with expected_outcome")
    if case.get("label_status") != "synthetic_unadjudicated":
        raise ValueError(f"{case['case_id']}: labels must remain explicitly marked synthetic and unadjudicated")
    adr_path = (CORPUS / case["adr_path"]).resolve()
    fixture_path = (CORPUS / case["fixture_path"]).resolve()
    if not adr_path.is_relative_to(CORPUS) or not fixture_path.is_relative_to(CORPUS):
        raise ValueError(f"{case['case_id']}: paths must remain under the corpus directory")
    if not adr_path.is_file() or sha256(adr_path) != case["adr_sha256"]:
        raise ValueError(f"{case['case_id']}: ADR file missing or hash mismatch")
    if case["requirement_excerpt"] not in adr_path.read_text(encoding="utf-8"):
        raise ValueError(f"{case['case_id']}: requirement excerpt is not present in its ADR")
    if not fixture_path.is_file() or sha256(fixture_path) != case["fixture_sha256"]:
        raise ValueError(f"{case['case_id']}: fixture missing or hash mismatch")
    fact = case["expected_fact"]
    if fact is not None and (not isinstance(fact, dict) or not isinstance(fact.get("path"), list) or "value" not in fact):
        raise ValueError(f"{case['case_id']}: expected_fact requires path and value")
    if case["expected_outcome"] == "inconclusive" and fact is not None:
        raise ValueError(f"{case['case_id']}: inconclusive corpus case cannot assert a known source fact")
    if fact is None and case["source_capability"] != "runtime_state":
        raise ValueError(f"{case['case_id']}: missing source fact must require runtime_state evidence")
    if fact is not None and case["source_capability"] != "declared_configuration":
        raise ValueError(f"{case['case_id']}: declared fixture fact must use declared_configuration capability")
    return adr_path, fixture_path


def run_audit() -> dict[str, Any]:
    cases = load_cases()
    if len(cases) != 50:
        raise ValueError(f"expected exactly 50 ADR cases; found {len(cases)}")
    adr_files = sorted((CORPUS / "adrs").glob("*.md"))
    case_adr_paths = {(CORPUS / case["adr_path"]).resolve() for case in cases}
    if len(adr_files) != 50 or {path.resolve() for path in adr_files} != case_adr_paths:
        raise ValueError(f"expected exactly 50 manifest-backed ADR Markdown files; found {len(adr_files)}")
    facts_checked = 0
    facts_matched = 0
    unsupported_cases = 0
    errors: list[dict[str, str]] = []
    details: list[dict[str, Any]] = []
    for case in cases:
        adr_path, fixture_path = validate_case(case)
        digest = sha256(fixture_path)
        artifact = {fixture_path.name: {
            "artifact_id": f"corpus:{case['case_id']}:fixture", "path": case["fixture_path"],
            "sha256": digest, "version": "sha256:" + digest,
        }}
        collected = observations.collect_configuration(fixture_path.parent, artifact)
        expected = case["expected_fact"]
        matched = False
        if expected is not None:
            facts_checked += 1
            matched = any(
                item["source_ref"].get("path") == case["fixture_path"]
                and item["source_ref"]["locator"].get("path") == expected["path"]
                and item.get("value") == expected["value"]
                for item in collected["observations"]
            )
            if matched:
                facts_matched += 1
            else:
                errors.append({"case_id": case["case_id"], "error": "expected source fact or exact locator was not emitted"})
            if not collected["coverage"].get("complete"):
                errors.append({"case_id": case["case_id"], "error": "supported configuration fixture has incomplete coverage"})
        else:
            unsupported_cases += 1
            if collected["coverage"].get("complete") or collected["observations"]:
                errors.append({"case_id": case["case_id"], "error": "unsupported-source case did not remain incomplete and observation-free"})
        details.append({
            "case_id": case["case_id"], "domain": case["domain"], "expected_outcome": case["expected_outcome"],
            "adr_sha256": case["adr_sha256"], "fixture_sha256": case["fixture_sha256"],
            "requirement_excerpt": case["requirement_excerpt"], "source_fact_matched": matched,
            "coverage_complete": bool(collected["coverage"].get("complete")),
            "observation_count": len(collected["observations"]), "diagnostics": collected["coverage"].get("diagnostics", []),
            "adr_path": adr_path.relative_to(CORPUS).as_posix(),
        })
    label_counts = Counter(case["expected_outcome"] for case in cases)
    domain_counts = Counter(case["domain"] for case in cases)
    return {
        "corpus_version": "adr-corpus-v1",
        "case_count": len(cases),
        "status": "pass" if not errors and facts_checked == facts_matched else "fail",
        "synthetic_unadjudicated_labels": True,
        "semantic_model_quality": "not_evaluated; no model invoked",
        "evidence_collection": {"checked": facts_checked, "matched": facts_matched, "accuracy": round(facts_matched / facts_checked, 4) if facts_checked else None},
        "unsupported_cases_remaining_inconclusive": unsupported_cases,
        "expected_outcome_counts": dict(sorted(label_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "errors": errors,
        "cases": details,
    }


def write_report(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "adr-corpus-evaluation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# ADR Corpus Audit", "", f"- Corpus: {result['corpus_version']}", f"- Cases: {result['case_count']}",
        f"- Audit status: {result['status']}", f"- Expected labels: {json.dumps(result['expected_outcome_counts'], sort_keys=True)}",
        f"- Domains: {json.dumps(result['domain_counts'], sort_keys=True)}",
        f"- Configuration facts matched: {result['evidence_collection']['matched']}/{result['evidence_collection']['checked']}",
        f"- Unsupported source cases retained as inconclusive: {result['unsupported_cases_remaining_inconclusive']}",
        f"- Semantic model quality: {result['semantic_model_quality']}",
        "", "Labels are synthetic and unadjudicated; this report measures corpus integrity and deterministic evidence collection, not semantic correctness or confidence calibration.",
        "", "## Errors", "",
    ]
    lines.extend([f"- {error['case_id']}: {error['error']}" for error in result["errors"]] or ["- None."])
    lines += ["", "## Cases", "", "| Case | Domain | Expected disposition | Fact collected | Coverage complete |", "|---|---|---|---:|---:|"]
    lines.extend(f"| {case['case_id']} | {case['domain']} | {case['expected_outcome']} | {case['source_fact_matched']} | {case['coverage_complete']} |" for case in result["cases"])
    (output_dir / "adr-corpus-evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = run_audit()
    write_report(result, Path(args.output_dir))
    print(f"ADR corpus audit: {result['status']} ({result['case_count']} cases; {result['evidence_collection']['matched']}/{result['evidence_collection']['checked']} facts matched)")
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
