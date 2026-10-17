#!/usr/bin/env python3
"""Simulate ADR discovery, applicability gating and evidence-linked deviation triage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from retrieval import load_jsonl, retrieve, sha

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / ".poc" / "scope" / "adr_catalog.jsonl"
DEFAULT_SCENARIOS = ROOT / ".poc" / "scope" / "scenarios.jsonl"


def event_text(event: dict[str, Any]) -> str:
    observations = event.get("source_observations", [])
    parts = [
        str(event.get("change_summary", "")),
        " ".join(event.get("evidence_terms", [])),
        "\n".join(str(o.get("excerpt", "")) + " " + str(o.get("claim", "")) for o in observations),
    ]
    return "\n".join(part for part in parts if part)


def assess_candidates(event: dict[str, Any], retrieval_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Conservative cue-based triage; every flag is a review candidate, never automatic proof."""
    corpus = event_text(event)
    candidates = []
    for adr in retrieval_result["selected_adrs"]:
        check = adr.get("deviation_check", {})
        violations, compliance = [], []
        for pattern in check.get("violation_patterns", []):
            if re.search(pattern, corpus, re.IGNORECASE):
                violations.append(pattern)
        for pattern in check.get("compliance_patterns", []):
            if re.search(pattern, corpus, re.IGNORECASE):
                compliance.append(pattern)

        if violations:
            disposition = "potential_deviation"
            rationale = (
                "One or more versioned deviation cues matched the supplied change/evidence text. "
                "This is a retrieval-plus-cue candidate, not proof; validate the executable path, "
                "normative wording, applicability and source locations before accepting it."
            )
        elif compliance:
            disposition = "no_conflict_signal"
            rationale = (
                "One or more alignment cues matched and no configured violation cue matched. "
                "This does not establish absence of deviation; inspect the full relevant path and branches."
            )
        else:
            disposition = "inconclusive"
            rationale = (
                "The ADR was retrieved, but the cue policy did not establish either conflict or alignment. "
                "Keep it visible for semantic assessment or human review."
            )

        observations = event.get("source_observations", [])
        evidence_refs = [{
            "evidence_id": f"{event.get('case_id', 'event')}:SRC:{i + 1}",
            "path": obs.get("path"),
            "line": obs.get("line"),
            "excerpt": obs.get("excerpt"),
            "claim": obs.get("claim"),
            "excerpt_sha256": sha(str(obs.get("excerpt", ""))),
        } for i, obs in enumerate(observations)]
        candidates.append({
            "adr_id": adr["adr_id"],
            "adr_version": adr["version"],
            "title": adr["title"],
            "finding_disposition": disposition,
            "control_id": check.get("check_id", "none"),
            "matched_violation_cues": violations,
            "matched_alignment_cues": compliance,
            "candidate_explanation": rationale,
            "requirement_excerpt": adr["normative_text"],
            "adr_source": {
                "path": adr["source_path"],
                "sha256": adr["source_sha256"],
                "chunk_id": adr["chunk_id"],
            },
            "source_observations": evidence_refs,
            "control_limitations": check.get("note", "No versioned cue policy is defined for this ADR."),
        })
    return candidates


def evaluate_event(event: dict[str, Any], catalog: list[dict[str, Any]], top_k: int,
                   in_scope_threshold: float, review_threshold: float) -> dict[str, Any]:
    retrieval_result = retrieve(
        event, catalog, top_k=top_k, in_scope_threshold=in_scope_threshold,
        review_threshold=review_threshold,
    )
    candidate_findings = assess_candidates(event, retrieval_result)
    flags = [x for x in candidate_findings if x["finding_disposition"] == "potential_deviation"]
    unresolved = [x for x in candidate_findings if x["finding_disposition"] == "inconclusive"]
    return {
        "event_id": event.get("case_id", event.get("event_id", "unknown")),
        "event_summary": event.get("change_summary", ""),
        "scope": retrieval_result,
        "candidate_assessments": candidate_findings,
        "triage": {
            "status": "review_required" if flags or unresolved or retrieval_result["disposition"] == "uncertain" else
                      "no_retrieved_adr" if retrieval_result["disposition"] == "not_in_scope" else "no_conflict_signal",
            "potential_deviation_count": len(flags),
            "inconclusive_count": len(unresolved),
            "supported_deviation_count": 0,
            "note": "This simulated pipeline never emits supported_deviation. That outcome requires semantic assessment plus evidence-link, citation, and provenance validation in the main pipeline.",
        },
    }


def metric_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    retrieved = [r for r in results if r["scope"]["selected_adrs"]]
    expected = [r for r in results if r.get("gold_disposition") == "in_scope"]
    recall_per_case = [
        len(set(r.get("gold_adr_ids", [])) & {a["adr_id"] for a in r["scope"]["selected_adrs"]}) /
        len(set(r.get("gold_adr_ids", [])))
        for r in expected if r.get("gold_adr_ids")
    ]
    by_label = {}
    for label in ("in_scope", "out_of_scope", "uncertain"):
        subset = [r for r in results if r.get("gold_disposition") == label]
        by_label[label] = {
            "cases": len(subset),
            "cases_with_any_retrieved_adr": sum(bool(r["scope"]["selected_adrs"]) for r in subset),
            "expected_adr_recall": (
                sum(set(r.get("gold_adr_ids", [])) <= {a["adr_id"] for a in r["scope"]["selected_adrs"]} for r in subset) / len(subset)
                if subset else None
            ),
        }
    false_in_scope = sum(r["scope"]["disposition"] == "in_scope" for r in results if r.get("gold_disposition") == "out_of_scope")
    return {
        "scenario_count": total,
        "retrieval_backend": "local_lexical_baseline",
        "selected_any_adr_count": len(retrieved),
        "expected_adr_recall_on_in_scope_cases": sum(recall_per_case) / len(recall_per_case) if recall_per_case else None,
        "false_in_scope_cases": false_in_scope,
        "scope_disposition_by_expected_label": by_label,
        "potential_deviation_flags": sum(r["triage"]["potential_deviation_count"] for r in results),
        "caveat": "Metrics are from a small synthetic fixture set and lexical baseline; not production retrieval performance or violation probability.",
    }


def fmt(value: Any) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def render_report(results: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    lines = [
        "# ADR Scope Retrieval and Deviation Triage — Simulation", "",
        f"- Scenarios: {metrics['scenario_count']}",
        f"- Backend: {metrics['retrieval_backend']}",
        f"- Expected ADR recall (in-scope cases): {fmt(metrics['expected_adr_recall_on_in_scope_cases'])}",
        f"- False in-scope dispositions on expected out-of-scope cases: {metrics['false_in_scope_cases']}",
        f"- Potential-deviation cues flagged: {metrics['potential_deviation_flags']}", "",
        "> This is a reproducible local lexical baseline, not Bedrock vector search. ADR applicability metadata is a hard gate before relevance ranking. Cue matches produce review candidates only; no result is promoted to supported_deviation without the main pipeline's evidence-link, citation, and provenance guards.",
        "", "## Scenario results", "",
        "| Scenario | Expected scope | Retrieval disposition | Selected ADRs | Potential flags | Triage |",
        "|---|---|---|---|---:|---|",
    ]
    for r in results:
        ids = ", ".join(f"{a['adr_id']} v{a['version']} ({a['score']:.2f})" for a in r["scope"]["selected_adrs"]) or "—"
        lines.append(
            f"| {r['event_id']} — {r['event_summary']} | {r.get('gold_disposition', '—')} | "
            f"{r['scope']['disposition']} | {ids} | {r['triage']['potential_deviation_count']} | {r['triage']['status']} |"
        )
    lines += ["", "## Candidate ADR evidence trails", ""]
    for r in results:
        lines += [f"### {r['event_id']}: {r['event_summary']}", ""]
        if not r["scope"]["selected_adrs"]:
            lines += [f"**Scope reason:** {r['scope']['reason']}", ""]
            if r["scope"]["review_candidates"]:
                lines.append("Review-only candidates: " + ", ".join(f"{a['adr_id']} ({a['score']:.2f})" for a in r["scope"]["review_candidates"]))
                lines.append("")
            continue
        for candidate in r["candidate_assessments"]:
            rel_score = next((a["score"] for a in r["scope"]["selected_adrs"] if a["adr_id"] == candidate["adr_id"]), 0)
            lines.append(f"- **{candidate['adr_id']} v{candidate['adr_version']} — {candidate['finding_disposition']}** (relevance {rel_score:.2f}; control {candidate['control_id']})")
            lines.append(f"  Requirement: {candidate['requirement_excerpt']}")
            lines.append(f"  Violation cues: {', '.join(candidate['matched_violation_cues']) or 'none'}")
            lines.append(f"  Alignment cues: {', '.join(candidate['matched_alignment_cues']) or 'none'}")
            lines.append(f"  Explanation: {candidate['candidate_explanation']}")
            lines.append(f"  ADR provenance: {candidate['adr_source']['path']} sha256={candidate['adr_source']['sha256']} chunk={candidate['adr_source']['chunk_id']}")
            for ev in candidate["source_observations"]:
                lines.append(f"  Observation: {ev['path']}:{ev['line']} — {ev['excerpt']} (sha256={ev['excerpt_sha256']})")
        lines.append("")
    lines += [
        "## Interpretation", "",
        "1. Scope detection is separate from deviation detection. Lifecycle and repository/service/domain/language constraints exclude ADRs before similarity ranking.",
        "2. Retrieval relevance is not truth. Scores rank lexical overlap against tags and normative text; they are not probabilities and should be replaced by hybrid vector+lexical relevance when wired to Aurora/pgvector.",
        "3. Flags are candidates. A cue match yields potential_deviation, not a supported finding. A no-match does not prove compliance.",
        "4. Provenance travels with the candidate: ADR ID/version/chunk/source hash plus source path/line/excerpt/hash references.",
        "5. Production next step: embed versioned ADR chunks with Bedrock, store vectors plus applicability metadata in Aurora PostgreSQL/pgvector, retrieve top-k with bound SQL parameters and metadata filters, then pass retrieved normative text to the existing structured assessment/evidence-link pipeline.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".poc" / "scope" / "output")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--in-scope-threshold", type=float, default=0.28)
    parser.add_argument("--review-threshold", type=float, default=0.14)
    args = parser.parse_args()
    catalog, scenarios = load_jsonl(args.catalog), load_jsonl(args.scenarios)
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for event in scenarios:
        result = evaluate_event(event, catalog, args.top_k, args.in_scope_threshold, args.review_threshold)
        result["gold_adr_ids"] = event.get("gold_adr_ids", [])
        result["gold_disposition"] = event.get("gold_disposition")
        result["description"] = event.get("description", "")
        results.append(result)
    metrics = metric_summary(results)
    payload = {
        "schema_version": "adr-scope-simulation-v1.0.0",
        "catalog_hash": results[0]["scope"]["audit"]["catalog_hash"] if results else "",
        "metrics": metrics,
        "results": results,
    }
    (out_dir / "scope-report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "scope-report.md").write_text(render_report(results, metrics), encoding="utf-8")
    print(f"Scope simulation complete: {len(results)} scenarios")
    print(f"Expected ADR recall: {fmt(metrics['expected_adr_recall_on_in_scope_cases'])}")
    print(f"Potential deviation cues: {metrics['potential_deviation_flags']}")
    print(f"Report: {out_dir / 'scope-report.md'}")


if __name__ == "__main__":
    main()
