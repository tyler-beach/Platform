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
        str(event.get("diff_summary", "")),
        " ".join(event.get("evidence_terms", [])),
        "\n".join(str(x) for x in event.get("normative_requirements", [])),
        "\n".join(str(x) for x in event.get("call_edges", [])),
        "\n".join(str(o.get("excerpt", "")) + " " + str(o.get("claim", "")) for o in observations),
    ]
    return "\n".join(part for part in parts if part)


def _observation_units(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Use source-backed excerpts/call edges, never retrieval keywords, as comparison evidence."""
    units: list[dict[str, Any]] = []
    for i, obs in enumerate(event.get("source_observations", []), start=1):
        excerpt = str(obs.get("excerpt", "")).strip()
        if not excerpt:
            continue
        units.append({
            "evidence_id": obs.get("evidence_id") or f"{event.get('case_id', event.get('event_id', 'event'))}:SRC:{i}",
            "artifact_id": obs.get("artifact_id"),
            "edge_id": obs.get("edge_id"),
            "evidence_type": obs.get("evidence_type", "source_observation"),
            "path": obs.get("path"),
            "line": obs.get("line", obs.get("start_line")),
            "excerpt": excerpt,
            "caller_qualified_name": obs.get("caller_qualified_name", ""),
            "callee_qualified_name": obs.get("callee_qualified_name", ""),
            "resolution_status": obs.get("resolution_status", ""),
            "claim": obs.get("claim", ""),
            "excerpt_sha256": sha(excerpt),
        })
    for i, line in enumerate(event.get("diff_lines", []), start=1):
        excerpt = str(line.get("excerpt", "") if isinstance(line, dict) else line).strip()
        if not excerpt:
            continue
        item = line if isinstance(line, dict) else {}
        units.append({
            "evidence_id": item.get("evidence_id") or f"{event.get('case_id', event.get('event_id', 'event'))}:DIFF:{i}",
            "artifact_id": item.get("artifact_id"),
            "edge_id": item.get("edge_id"),
            "evidence_type": "diff_line",
            "path": item.get("path"),
            "line": item.get("line", item.get("start_line")),
            "excerpt": excerpt,
            "caller_qualified_name": item.get("caller_qualified_name", ""),
            "callee_qualified_name": item.get("callee_qualified_name", ""),
            "resolution_status": item.get("resolution_status", ""),
            "excerpt_sha256": sha(excerpt),
        })
    return units


def _match_cue(pattern: str, unit: dict[str, Any]) -> bool:
    try:
        return re.search(pattern, unit["excerpt"], re.IGNORECASE) is not None
    except re.error:
        # Invalid catalog rules should not silently create a match or crash the run.
        return False


def _cue_record(pattern: str, unit: dict[str, Any], relationship: str, explanation: str) -> dict[str, Any]:
    return {
        "relationship": relationship,
        "rule": pattern,
        "evidence_id": unit["evidence_id"],
        "path": unit.get("path"),
        "line": unit.get("line"),
        "excerpt": unit["excerpt"],
        "excerpt_sha256": unit["excerpt_sha256"],
        "explanation": explanation,
    }


def assess_candidates(event: dict[str, Any], retrieval_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare each matched active ADR with pinned source/diff evidence.

    This local baseline uses explicit cue rules. In production, a semantic model can
    propose the comparison, but every result must still cite the ADR requirement and
    source observations, and then pass deterministic validation.
    """
    units = _observation_units(event)
    matches = []
    for adr in retrieval_result["selected_adrs"]:
        check = adr.get("deviation_check", {})
        cue_links: list[dict[str, Any]] = []

        for pattern in check.get("violation_patterns", []):
            for unit in units:
                if not _match_cue(pattern, unit):
                    continue
                relationship = "contradicts"
                explanation = "A source-backed excerpt matched a versioned contradiction cue."
                # A provider call alone is not a violation: for the async-provider ADR,
                # the call site must be on the request path; a worker call is alignment,
                # and a missing caller identity remains uncertain.
                if adr.get("adr_id") == "ADR-001" and "Provider" in pattern:
                    caller = str(unit.get("caller_qualified_name", ""))
                    if re.search(r"(worker|consumer|async|background)", caller, re.IGNORECASE):
                        relationship = "consistent_with"
                        explanation = "Provider call is attributed to an asynchronous worker/consumer, not the request handler."
                    elif not caller:
                        relationship = "uncertain"
                        explanation = "Provider call was found, but caller identity is absent; sync-vs-async behavior is not established."
                    elif not re.search(r"(handler|controller|submit|request|endpoint)", caller, re.IGNORECASE):
                        relationship = "uncertain"
                        explanation = "Provider call was found, but caller identity does not establish whether this is the synchronous request path."
                cue_links.append(_cue_record(pattern, unit, relationship, explanation))

        for pattern in check.get("compliance_patterns", []):
            for unit in units:
                if _match_cue(pattern, unit):
                    cue_links.append(_cue_record(
                        pattern, unit, "consistent_with",
                        "A source-backed excerpt matched a versioned alignment cue.",
                    ))

        contradictions = [x for x in cue_links if x["relationship"] == "contradicts"]
        alignments = [x for x in cue_links if x["relationship"] == "consistent_with"]
        unresolved_links = [x for x in cue_links if x["relationship"] == "uncertain"]
        if contradictions and alignments:
            result = "uncertain"
            rationale = "Evidence contains both contradiction and alignment cues; keep the ADR comparison unresolved for semantic/reviewer adjudication."
        elif contradictions:
            result = "deviation"
            rationale = "Source-backed evidence matches a versioned contradiction cue for this active ADR. This is a candidate deviation and must pass production semantic/evidence validation."
        elif alignments and not unresolved_links:
            result = "aligned"
            rationale = "Source-backed evidence matches an alignment cue and no contradiction cue matched. This is provisional alignment, not a proof that every code path complies."
        else:
            result = "uncertain"
            rationale = "The active ADR matched the event scope, but available source-backed evidence does not establish alignment or deviation."

        requirement_id = f"{adr.get('chunk_id', adr['adr_id'])}:REQUIREMENT"
        requirement_hash = sha(str(adr.get("normative_text", "")))
        evidence_links = []
        for index, link in enumerate(cue_links, start=1):
            evidence_links.append({
                "link_id": f"{requirement_id}:LINK:{index}",
                "requirement_evidence_id": requirement_id,
                "observation_evidence_id": link["evidence_id"],
                "relationship": link["relationship"],
                "rule": link["rule"],
                "explanation": link["explanation"],
            })
        matches.append({
            "adr_id": adr["adr_id"],
            "adr_version": adr["version"],
            "chunk_id": adr["chunk_id"],
            "title": adr["title"],
            "applicability": "matched_active_adr",
            "comparison_result": result,
            "match_status": "matched",
            "control_id": check.get("check_id", "none"),
            "matched_violation_cues": [x["rule"] for x in contradictions],
            "matched_alignment_cues": [x["rule"] for x in alignments],
            "candidate_explanation": rationale,
            "requirement_evidence": {
                "evidence_id": requirement_id,
                "artifact_id": adr.get("chunk_id"),
                "path": adr.get("source_path"),
                "line": adr.get("source_line_start", 1),
                "excerpt": adr.get("normative_text", ""),
                "excerpt_sha256": requirement_hash,
                "source_sha256": adr.get("source_sha256"),
            },
            "adr_source": {
                "path": adr["source_path"],
                "sha256": adr["source_sha256"],
                "chunk_id": adr["chunk_id"],
            },
            "source_observations": units,
            "evidence_links": evidence_links,
            "matched_cue_evidence": cue_links,
            "control_limitations": check.get("note", "No versioned cue policy is defined for this ADR."),
        })
    return matches

def evaluate_event(event: dict[str, Any], catalog: list[dict[str, Any]], top_k: int,
                   in_scope_threshold: float, review_threshold: float, backend: str = "local") -> dict[str, Any]:
    if backend == "aurora":
        from aurora_backend import retrieve_from_aurora
        retrieval_result = retrieve_from_aurora(
            event, top_k=top_k, in_scope_threshold=in_scope_threshold,
            review_threshold=review_threshold,
        )
    else:
        retrieval_result = retrieve(
            event, catalog, top_k=top_k, in_scope_threshold=in_scope_threshold,
            review_threshold=review_threshold,
        )
    adr_matches = assess_candidates(event, retrieval_result)
    deviations = [x for x in adr_matches if x["comparison_result"] == "deviation"]
    aligned = [x for x in adr_matches if x["comparison_result"] == "aligned"]
    unresolved = [x for x in adr_matches if x["comparison_result"] == "uncertain"]
    if deviations:
        overall_result = "deviation"
    elif unresolved:
        overall_result = "uncertain"
    elif aligned:
        overall_result = "aligned"
    elif retrieval_result["disposition"] == "uncertain":
        overall_result = "uncertain"
    else:
        overall_result = "no_applicable_adr"
    return {
        "event_id": event.get("case_id", event.get("event_id", "unknown")),
        "event_summary": event.get("change_summary", ""),
        "scope": retrieval_result,
        "adr_matches": adr_matches,
        "candidate_assessments": adr_matches,
        "comparison": {
            "overall_result": overall_result,
            "matched_active_adr_count": len(adr_matches),
            "deviation_count": len(deviations),
            "aligned_count": len(aligned),
            "uncertain_count": len(unresolved),
            "note": "Local comparison uses auditable cue rules over source-backed observations. Deviations and alignments are provisional labels; production model assessments must link each ADR requirement to exact evidence and pass schema/provenance validation.",
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
        with_expected_adrs = [r for r in subset if r.get("gold_adr_ids")]
        by_label[label] = {
            "cases": len(subset),
            "cases_with_any_retrieved_adr": sum(bool(r["scope"]["selected_adrs"]) for r in subset),
            "expected_adr_recall": (
                sum(set(r.get("gold_adr_ids", [])) <= {a["adr_id"] for a in r["scope"]["selected_adrs"]} for r in with_expected_adrs) / len(with_expected_adrs)
                if with_expected_adrs else None
            ),
        }
    false_in_scope = sum(
        r["scope"]["disposition"] == "in_scope"
        for r in results if r.get("gold_disposition") == "out_of_scope"
    )
    comparison_cases = [r for r in results if r.get("gold_comparison")]
    comparison_labels = ("deviation", "aligned", "uncertain", "no_applicable_adr")
    confusion = {gold: {pred: 0 for pred in comparison_labels} for gold in comparison_labels}
    for row in comparison_cases:
        gold, pred = row["gold_comparison"], row["comparison"]["overall_result"]
        if gold in confusion and pred in comparison_labels:
            confusion[gold][pred] += 1
    exact = sum(r["comparison"]["overall_result"] == r["gold_comparison"] for r in comparison_cases)
    return {
        "scenario_count": total,
        "retrieval_backend": results[0]["scope"]["backend"] if results else "local_lexical_baseline",
        "selected_any_adr_count": len(retrieved),
        "expected_adr_recall_on_in_scope_cases": sum(recall_per_case) / len(recall_per_case) if recall_per_case else None,
        "false_in_scope_cases": false_in_scope,
        "scope_disposition_by_expected_label": by_label,
        "comparison_case_count": len(comparison_cases),
        "comparison_exact_agreement": exact / len(comparison_cases) if comparison_cases else None,
        "comparison_confusion_matrix": confusion,
        "comparison_counts": {
            "deviation": sum(r["comparison"]["overall_result"] == "deviation" for r in results),
            "aligned": sum(r["comparison"]["overall_result"] == "aligned" for r in results),
            "uncertain": sum(r["comparison"]["overall_result"] == "uncertain" for r in results),
            "no_applicable_adr": sum(r["comparison"]["overall_result"] == "no_applicable_adr" for r in results),
        },
        "caveat": "Metrics are from small synthetic fixtures and a lexical retrieval/cue-rule comparison baseline; not production model performance or calibrated probabilities.",
    }

def fmt(value: Any) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def render_report(results: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    lines = [
        "# ADR Matches and Alignment/Deviation Report — Simulation", "",
        f"- Scenarios: {metrics['scenario_count']}",
        f"- Backend: {metrics['retrieval_backend']}",
        f"- Expected ADR recall (in-scope scenarios): {fmt(metrics['expected_adr_recall_on_in_scope_cases'])}",
        f"- Comparison exact agreement on labeled cases: {fmt(metrics['comparison_exact_agreement'])}",
        f"- Matched ADR comparison counts: {json.dumps(metrics['comparison_counts'], sort_keys=True)}", "",
        "> The local baseline ranks active ADRs, then compares source-backed excerpts to transparent versioned cues. Each ADR result is aligned, deviation, or uncertain. A cue-based deviation is a review candidate, not an automatically accepted enforcement finding.",
        "", "## Scenario results", "",
        "| Scenario | Expected comparison | Retrieval disposition | Active ADR matches | Overall comparison |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        ids = ", ".join(
            f"{a['adr_id']} v{a['version']} ({a['score']:.2f})"
            for a in r["scope"]["selected_adrs"]
        ) or "—"
        lines.append(
            f"| {r['event_id']} — {r['event_summary']} | {r.get('gold_comparison', '—')} | "
            f"{r['scope']['disposition']} | {ids} | {r['comparison']['overall_result']} |"
        )
    lines += ["", "## Per-ADR comparisons and evidence", ""]
    for r in results:
        lines += [f"### {r['event_id']}: {r['event_summary']}", ""]
        if not r["adr_matches"]:
            lines += [f"**Comparison:** {r['comparison']['overall_result']}. {r['scope']['reason']}", ""]
            if r["scope"]["review_candidates"]:
                lines.append("Active ADRs available for review (not treated as confirmed matches): " +
                             ", ".join(f"{a['adr_id']} ({a['score']:.2f})" for a in r["scope"]["review_candidates"]))
                lines.append("")
            continue
        for match in r["adr_matches"]:
            relevance = next(
                (a["score"] for a in r["scope"]["selected_adrs"] if a["adr_id"] == match["adr_id"]), 0
            )
            lines.append(
                f"- **{match['adr_id']} v{match['adr_version']} — {match['comparison_result']}** "
                f"(active ADR match; retrieval similarity {relevance:.2f}; control {match['control_id']})"
            )
            lines.append(f"  Normative requirement ({match['requirement_evidence']['evidence_id']}): {match['requirement_evidence']['excerpt']}")
            lines.append(f"  Explanation: {match['candidate_explanation']}")
            lines.append(f"  ADR provenance: {match['adr_source']['path']} sha256={match['adr_source']['sha256']} chunk={match['adr_source']['chunk_id']}")
            if not match["evidence_links"]:
                lines.append("  Evidence links: none; current observations did not trigger a comparison cue.")
            for link in match["evidence_links"]:
                lines.append(
                    f"  Evidence link: {link['relationship']} — requirement {link['requirement_evidence_id']} "
                    f"to observation {link['observation_evidence_id']} via {link['rule']}: {link['explanation']}"
                )
            for ev in match["source_observations"]:
                lines.append(
                    f"  Observation: {ev.get('path')}:{ev.get('line')} — {ev['excerpt']} "
                    f"(evidence={ev['evidence_id']}; sha256={ev['excerpt_sha256']})"
                )
        lines.append("")
    lines += [
        "## Interpretation", "",
        "1. Retrieval only decides which active ADRs are candidate matches. The comparison result is emitted per matched ADR.",
        "2. Deviation means a source-backed excerpt matched a contradiction cue; aligned means alignment cues matched without contradictory cues; uncertain means evidence is missing, conflicting, or not decisive.",
        "3. Exact source excerpts are used for comparison cues. Change summaries and retrieval terms help search, but cannot by themselves trigger an alignment/deviation result.",
        "4. A provider call from a known worker is not treated as a deviation of the asynchronous-provider ADR. If caller identity is missing, the result remains uncertain.",
        "5. Retired/superseded ADRs are filtered before lexical/vector ranking. They do not produce matches, evidence links, or influence the comparison result.",
        "6. In production, replace deterministic cues with structured semantic assessment while preserving the per-ADR result schema, requirement-to-observation links, source hashes and lifecycle filters.",
        "",
    ]
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--event-json", type=Path, default=None,
                        help="run one supplied change/evidence event instead of the labeled scenarios")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".poc" / "scope" / "output")
    parser.add_argument("--backend", choices=("local", "aurora"), default="local",
                        help="local is offline lexical search; aurora uses Bedrock embeddings and Aurora pgvector")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--in-scope-threshold", type=float, default=None)
    parser.add_argument("--review-threshold", type=float, default=None)
    args = parser.parse_args()
    if args.in_scope_threshold is None:
        args.in_scope_threshold = 0.55 if args.backend == "aurora" else 0.28
    if args.review_threshold is None:
        args.review_threshold = 0.43 if args.backend == "aurora" else 0.14
    catalog = load_jsonl(args.catalog)
    if args.event_json:
        event_path = args.event_json if args.event_json.is_absolute() else ROOT / args.event_json
        event = json.loads(event_path.read_text(encoding="utf-8"))
        required_fields = ("repository", "service", "domain", "language", "change_summary")
        missing = [field for field in required_fields if not event.get(field)]
        if missing:
            parser.error("event JSON is missing required field(s): " + ", ".join(missing))
        if not event.get("source_observations") and not event.get("diff_lines"):
            parser.error("event JSON must include source_observations or exact diff_lines; summaries alone are not comparison evidence")
        scenarios = [event]
    else:
        scenarios = load_jsonl(args.scenarios)
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for event in scenarios:
        result = evaluate_event(event, catalog, args.top_k, args.in_scope_threshold, args.review_threshold, args.backend)
        result["gold_adr_ids"] = event.get("gold_adr_ids", [])
        result["gold_disposition"] = event.get("gold_disposition")
        result["description"] = event.get("description", "")
        results.append(result)
    metrics = metric_summary(results)
    payload = {
        "schema_version": "adr-scope-simulation-v1.0.0",
        "catalog_hash": results[0]["scope"].get("audit", {}).get("catalog_hash", "") if results else "",
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
