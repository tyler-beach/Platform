#!/usr/bin/env python3
"""Run the labeled PoC evaluation set against mock or Anthropic.

The mock provider is the safe default. Scores remain evidence-support ratings;
this harness evaluates decisions and threshold-gated review behavior, not probabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc"))
os.chdir(ROOT)

import confidence  # noqa: E402
import model  # noqa: E402

CASES_PATH = ROOT / ".poc" / "evaluation" / "cases.jsonl"
LABELS = ("deviation", "no_deviation", "ambiguous")
OUTCOME_TO_LABEL = {
    "supported_deviation": "deviation",
    "no_deviation_found": "no_deviation",
    "potential_deviation": "ambiguous",
    "inconclusive": "ambiguous",
}
ENTRY_ID = "F-ENTRY"
WORKER_ID = "F-WORKER"
HELPER_ID = "F-HELPER"
PROVIDER_ID = "F-PROVIDER"
VALIDATOR_ID = "F-VALIDATOR"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cases() -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique")
    for case in cases:
        if case.get("gold_label") not in LABELS:
            raise ValueError(f"{case.get('case_id')}: invalid gold_label")
    counts = Counter(case["gold_label"] for case in cases)
    if any(counts[label] == 0 for label in LABELS):
        raise ValueError("Evaluation set must include deviation, no_deviation, and ambiguous labels")
    return cases


def build_case_context(case: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Expand a declarative scenario into a pinned synthetic evidence package."""
    cid = case["case_id"]
    behavior = case["behavior"]
    edges: list[dict[str, Any]] = []
    functions = [
        {"symbol_id": ENTRY_ID, "qualified_name": "Handler.Submit", "entry_path_edge_ids": []},
        {"symbol_id": WORKER_ID, "qualified_name": "Worker.Execute", "entry_path_edge_ids": []},
        {"symbol_id": HELPER_ID, "qualified_name": "AssessmentService.Run", "entry_path_edge_ids": []},
        {"symbol_id": PROVIDER_ID, "qualified_name": "AnthropicClient.Assess", "entry_path_edge_ids": []},
        {"symbol_id": VALIDATOR_ID, "qualified_name": "InputValidator.Assess", "entry_path_edge_ids": []},
    ]

    def add_edge(caller: str, callee: str, callee_name: str, expression: str,
                 resolution: str = "resolved_static", dispatch: str = "static") -> None:
        idx = len(edges) + 1
        edge = {
            "edge_id": f"{cid}:EDGE-{idx}",
            "caller_symbol_id": caller,
            "callee_symbol_id": callee if resolution not in {"unresolved", "unresolved_dynamic"} else None,
            "caller_qualified_name": next((f["qualified_name"] for f in functions if f["symbol_id"] == caller), caller),
            "callee_qualified_name": callee_name,
            "call_expression": expression,
            "resolution_status": resolution,
            "resolution_basis": {
                "resolved_static": "compiler_symbol_binding",
                "resolved_approximate": "cha_possible_target",
                "unresolved_dynamic": "dynamic_receiver_unresolved",
                "unresolved": "symbol_binding_unresolved",
            }.get(resolution, "compiler_symbol_binding"),
            "dispatch_kind": dispatch,
            "is_transitive": caller != ENTRY_ID,
            "reachable_from_entry": True,
        }
        edges.append(edge)
        if caller == WORKER_ID:
            worker = next(f for f in functions if f["symbol_id"] == WORKER_ID)
            worker["entry_path_edge_ids"] = [x["edge_id"] for x in edges if x["caller_symbol_id"] == ENTRY_ID]
        if caller == HELPER_ID:
            helper = next(f for f in functions if f["symbol_id"] == HELPER_ID)
            helper["entry_path_edge_ids"] = [x["edge_id"] for x in edges if x["caller_symbol_id"] == ENTRY_ID]
        if callee == PROVIDER_ID:
            provider = next(f for f in functions if f["symbol_id"] == PROVIDER_ID)
            provider["entry_path_edge_ids"] = (
                [x["edge_id"] for x in edges if x["caller_symbol_id"] == ENTRY_ID]
                if caller == ENTRY_ID else
                [x["edge_id"] for x in edges if x["caller_symbol_id"] in {ENTRY_ID, HELPER_ID, WORKER_ID}]
            )

    if behavior in {"direct_provider", "ambiguous_fallback", "direct_conditional", "unresolved_provider"}:
        expression = case["observation"]
        status = case.get("entry_status", "resolved_static")
        if behavior == "unresolved_provider":
            status = "unresolved_dynamic"
        add_edge(ENTRY_ID, PROVIDER_ID, "Provider.Assess", expression, status, case.get("dispatch", "static"))
    elif behavior == "direct_validator":
        add_edge(ENTRY_ID, VALIDATOR_ID, "InputValidator.Assess", case["observation"], "resolved_static", "static")
    elif behavior == "queue_then_worker":
        add_edge(ENTRY_ID, "F-QUEUE", "Queue.Enqueue", "return h.Queue.Enqueue(ctx, req)", "resolved_static", "static")
        add_edge(WORKER_ID, PROVIDER_ID, "AnthropicClient.Assess", "return w.Provider.Assess(ctx, req)", case.get("worker_edge_status", "resolved_static"), "static")
    elif behavior == "helper_sync_provider":
        add_edge(ENTRY_ID, HELPER_ID, "AssessmentService.Run", "return s.Run(ctx, req)", "resolved_static", "static")
        add_edge(HELPER_ID, PROVIDER_ID, "AnthropicClient.Assess", "return s.Provider.Assess(ctx, req)", case.get("worker_edge_status", "resolved_static"), "static")
    elif behavior == "no_provider":
        add_edge(ENTRY_ID, "F-QUEUE", "Queue.Enqueue", "return h.Queue.Enqueue(ctx, req)", "resolved_static", "static")
    else:
        raise ValueError(f"{cid}: unsupported behavior {behavior}")

    graph = {
        "resolver": "labeled-evaluation-synthetic-graph-v1",
        "entry_resolution": "resolved",
        "entry_symbol_ids": [ENTRY_ID],
        "functions": functions,
        "edges": edges,
        "reachable_edges": [dict(edge) for edge in edges],
        "reachable_functions": [f["symbol_id"] for f in functions],
        "diagnostics": [],
    }

    requirement = case["requirement"]
    doc_artifact = {
        "artifact_id": f"{cid}:ART-DOC",
        "path": f"evaluation/{cid}/ADR.md",
        "sha256": sha(requirement),
        "byte_length": len(requirement.encode("utf-8")),
        "version": "evaluation-case-v1",
    }
    source_text = "\n".join(edge["call_expression"] for edge in edges)
    source_artifact = {
        "artifact_id": f"{cid}:ART-SRC",
        "path": f"evaluation/{cid}/source.txt",
        "sha256": sha(source_text),
        "byte_length": len(source_text.encode("utf-8")),
        "version": "evaluation-case-v1",
    }
    artifacts = [source_artifact, doc_artifact]
    evidence: list[dict[str, Any]] = []
    if case.get("has_normative", True):
        evidence.append({
            "evidence_id": f"{cid}:REQ",
            "evidence_type": "normative_requirement",
            "artifact_id": doc_artifact["artifact_id"],
            "path": doc_artifact["path"],
            "start_line": 5,
            "end_line": 5,
            "excerpt": requirement,
            "claim": requirement,
            "sha256": sha(requirement),
        })
    for idx, edge in enumerate(edges, start=1):
        excerpt = edge["call_expression"]
        evidence.append({
            "evidence_id": f"{cid}:OBS-{idx}",
            "evidence_type": "unresolved_call_edge" if edge["resolution_status"] in {"unresolved", "unresolved_dynamic"} else "resolved_call_edge",
            "artifact_id": source_artifact["artifact_id"],
            "edge_id": edge["edge_id"],
            "path": source_artifact["path"],
            "start_line": 20 + idx,
            "end_line": 20 + idx,
            "excerpt": excerpt,
            "claim": f"Call edge {edge['caller_qualified_name']} -> {edge['callee_qualified_name']}",
            "sha256": sha(excerpt),
        })

    diff_excerpt = str(case.get("diff_excerpt", "")).strip()
    if diff_excerpt:
        diff_artifact = {
            "artifact_id": f"{cid}:ART-DIFF",
            "path": f"evaluation/{cid}/change.diff",
            "sha256": sha(diff_excerpt),
            "byte_length": len(diff_excerpt.encode("utf-8")),
            "version": "evaluation-case-v1",
        }
        artifacts.append(diff_artifact)
        evidence.append({
            "evidence_id": f"{cid}:DIFF",
            "evidence_type": "diff_line",
            "artifact_id": diff_artifact["artifact_id"],
            "path": diff_artifact["path"],
            "start_line": 1,
            "end_line": 1,
            "excerpt": diff_excerpt,
            "claim": "Change evidence: " + diff_excerpt,
            "sha256": sha(diff_excerpt),
        })

    context = {
        "comparison": "spec-vs-implementation",
        "root_symbol": "Handler.Submit",
        "requirements": requirement,
        "graph": graph,
        "evidence": evidence,
        "graph_evidence": json.dumps({
            "entry": "Handler.Submit",
            "edges": [{k: e.get(k) for k in ("edge_id", "caller_qualified_name", "callee_qualified_name", "resolution_status", "resolution_basis", "dispatch_kind", "call_expression")} for e in edges],
        }, indent=2),
        "evidence_items": json.dumps(evidence, indent=2),
        "diff_excerpt": diff_excerpt,
    }
    return context, artifacts


def label_outcome(outcome: str) -> str:
    return OUTCOME_TO_LABEL.get(outcome, "ambiguous")


def score_binary(labels: list[str], predicted_positive: list[bool]) -> dict[str, Any]:
    tp = sum(label == "deviation" and pred for label, pred in zip(labels, predicted_positive))
    fp = sum(label == "no_deviation" and pred for label, pred in zip(labels, predicted_positive))
    fn = sum(label == "deviation" and not pred for label, pred in zip(labels, predicted_positive))
    tn = sum(label == "no_deviation" and not pred for label, pred in zip(labels, predicted_positive))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    exact = sum(r["predicted_label"] == r["gold_label"] for r in results)
    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    for result in results:
        confusion[result["gold_label"]][result["predicted_label"]] += 1
    clear = [r for r in results if r["gold_label"] != "ambiguous"]
    clear_binary = score_binary(
        [r["gold_label"] for r in clear],
        [r["predicted_label"] == "deviation" for r in clear],
    )
    ambiguous = [r for r in results if r["gold_label"] == "ambiguous"]
    ambiguous_escalation_rate = (
        sum(r["predicted_label"] == "ambiguous" for r in ambiguous) / len(ambiguous)
        if ambiguous else None
    )
    # Break down outcomes by the deterministic scenario family so a good
    # aggregate score cannot hide a systematic failure in one graph pattern.
    by_behavior: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_behavior.setdefault(str(result.get("behavior", "unspecified")), []).append(result)
    behavior_metrics = {}
    for behavior, rows in sorted(by_behavior.items()):
        row_total = len(rows)
        row_correct = sum(r["predicted_label"] == r["gold_label"] for r in rows)
        row_clear = [r for r in rows if r["gold_label"] != "ambiguous"]
        row_binary = score_binary(
            [r["gold_label"] for r in row_clear],
            [r["predicted_label"] == "deviation" for r in row_clear],
        )
        behavior_metrics[behavior] = {
            "case_count": row_total,
            "three_way_correct": row_correct,
            "exact_three_way_accuracy": row_correct / row_total if row_total else None,
            "label_counts": dict(Counter(r["gold_label"] for r in rows)),
            "clear_case_binary_metrics": row_binary,
            "ambiguous_case_count": sum(r["gold_label"] == "ambiguous" for r in rows),
            "ambiguous_escalated": sum(r["gold_label"] == "ambiguous" and r["predicted_label"] == "ambiguous" for r in rows),
        }
    threshold_sweep = []
    for threshold in (0, 50, 60, 70, 80, 85, 90, 95, 100):
        accepted = [
            r for r in clear
            if r["accepted_outcome"] == "supported_deviation" and r["score_0_to_100"] >= threshold
        ]
        gated_stats = score_binary(
            [r["gold_label"] for r in clear],
            [r in accepted for r in clear],
        )
        gated_stats["threshold"] = threshold
        gated_stats["actionable_findings"] = len(accepted)
        threshold_sweep.append(gated_stats)
    return {
        "case_count": total,
        "label_counts": dict(Counter(r["gold_label"] for r in results)),
        "exact_three_way_accuracy": exact / total if total else None,
        "three_way_correct": exact,
        "confusion_matrix": confusion,
        "clear_case_count": len(clear),
        "clear_case_binary_metrics": clear_binary,
        "clear_case_decision_coverage": (
            sum(r["predicted_label"] != "ambiguous" for r in clear) / len(clear) if clear else None
        ),
        "ambiguous_case_count": len(ambiguous),
        "ambiguous_case_escalation_rate": ambiguous_escalation_rate,
        "review_gate_threshold_sweep": threshold_sweep,
        "by_behavior": behavior_metrics,
        "interpretation": (
            "Evidence-strength scores are not probabilities. Threshold results show only how a "
            "score gate changes findings sent forward for human review; they do not establish "
            "probability calibration or justify unattended enforcement."
        ),
    }


def fmt_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def write_report(path: Path, provider: str, results: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    lines = [
        "# Labeled ADR Deviation Evaluation",
        "",
        f"- Provider: {provider}",
        f"- Dataset: {CASES_PATH.relative_to(ROOT)}",
        f"- Cases: {metrics['case_count']}",
        f"- Labels: {json.dumps(metrics['label_counts'], sort_keys=True)}",
        f"- Three-way exact accuracy: {metrics['exact_three_way_accuracy']:.1%}",
        f"- Clear-case decision coverage: {metrics['clear_case_decision_coverage']:.1%}",
        f"- Escalation rate on ambiguous gold cases: {metrics['ambiguous_case_escalation_rate']:.1%}",
        "",
        "## Results by scenario family",
        "",
        "| Family | Cases | Exact accuracy | TP | FP | FN | TN |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *[
            f"| {family} | {row['case_count']} | {fmt_metric(row['exact_three_way_accuracy'])} | "
            f"{row['clear_case_binary_metrics']['tp']} | {row['clear_case_binary_metrics']['fp']} | "
            f"{row['clear_case_binary_metrics']['fn']} | {row['clear_case_binary_metrics']['tn']} |"
            for family, row in sorted(metrics.get("by_behavior", {}).items())
        ],
        "",
        "> **Interpretation guardrail:** These are initial synthetic, hand-authored evaluation cases. They are a regression harness, not an independently adjudicated benchmark or a calibration claim. Evidence scores are not probabilities; threshold results describe review gating only.",
        "",
        "## Results by case",
        "",
        "| Case | Gold label | Predicted label | Proposed outcome | Accepted outcome | Evidence score | Exact match |",
        "|---|---|---|---|---|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['case_id']} — {r['title']} | {r['gold_label']} | {r['predicted_label']} | "
            f"{r['proposed_outcome']} | {r['accepted_outcome']} | {r['score_0_to_100']:.1f} | "
            f"{'yes' if r['predicted_label'] == r['gold_label'] else 'no'} |"
        )
    lines += [
        "",
        "## Clear-case binary metrics",
        "",
        "Ambiguous gold cases are excluded from binary true/false violation counts.",
        "",
        f"- TP: {metrics['clear_case_binary_metrics']['tp']}",
        f"- FP: {metrics['clear_case_binary_metrics']['fp']}",
        f"- FN: {metrics['clear_case_binary_metrics']['fn']}",
        f"- TN: {metrics['clear_case_binary_metrics']['tn']}",
        f"- Precision: {fmt_metric(metrics['clear_case_binary_metrics']['precision'])}",
        f"- Recall: {fmt_metric(metrics['clear_case_binary_metrics']['recall'])}",
        f"- F1: {fmt_metric(metrics['clear_case_binary_metrics']['f1'])}",
        "",
        "## Review-gate threshold sweep",
        "",
        "| Minimum evidence score | Actionable findings | TP | FP | FN | TN | Precision | Recall |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in metrics["review_gate_threshold_sweep"]:
        lines.append(
            f"| {r['threshold']} | {r['actionable_findings']} | {r['tp']} | {r['fp']} | {r['fn']} | {r['tn']} | "
            f"{fmt_metric(r['precision'])} | {fmt_metric(r['recall'])} |"
        )
    lines += [
        "",
        "## Confusion matrix",
        "",
        "| Gold / Predicted | Deviation | No deviation | Ambiguous |",
        "|---|---:|---:|---:|",
    ]
    for gold in LABELS:
        lines.append(
            f"| {gold} | {metrics['confusion_matrix'][gold]['deviation']} | "
            f"{metrics['confusion_matrix'][gold]['no_deviation']} | {metrics['confusion_matrix'][gold]['ambiguous']} |"
        )
    lines += [
        "",
        "## Limitations and use",
        "",
        "- Labels are provisional scenario-level expected dispositions, not external ground truth. Have architecture reviewers independently adjudicate and version the cases before using any metric to tune operational policy.",
        "- This small suite is designed to expose decision-boundary failures; its aggregate metrics are not representative estimates of production performance.",
        "- The mock provider evaluates its own deterministic rules, not LLM quality. Use --provider anthropic only when an explicit, budgeted live-model evaluation is intended.",
        "- A high evidence score means the cited support package is internally stronger under the current rubric. It does not mean a deviation is more likely to be true.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("mock", "anthropic"), default="mock",
                        help="mock is offline and deterministic; anthropic makes live API calls")
    parser.add_argument("--max-output-tokens", type=int, default=1000)
    parser.add_argument("--output-dir", default=".poc/evaluation/output")
    args = parser.parse_args()

    cases = load_cases()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        context, artifacts = build_case_context(case)
        envelope = model.assess(args.provider, context, max_output_tokens=args.max_output_tokens)
        assessment = envelope["assessment"]
        score = confidence.score_assessment(
            graph=context["graph"],
            syntax={"files": [{"errors": []}]},
            evidence=context["evidence"],
            artifact_rows=artifacts,
            cited_ids=assessment.get("evidence_ids", []),
            evidence_links=assessment.get("evidence_links", []),
            proposed_outcome=assessment.get("outcome", "inconclusive"),
        )
        accepted = score["accepted_outcome"]
        results.append({
            "case_id": case["case_id"],
            "title": case["title"],
            "gold_label": case["gold_label"],
            "provider": envelope["provider"],
            "model": envelope["model"],
            "proposed_outcome": assessment.get("outcome", "inconclusive"),
            "accepted_outcome": accepted,
            "predicted_label": label_outcome(accepted),
            "model_self_reported_confidence": assessment.get("confidence"),
            "score": score["score"],
            "score_0_to_100": score["score_0_to_100"],
            "score_band": score["band"],
            "score_algorithm": score["algorithm_version"],
            "score_is_calibrated_probability": score["is_calibrated_probability"],
            "evidence_ids": assessment.get("evidence_ids", []),
            "evidence_links": score["evidence_links"],
            "guardrails": score["guardrails"],
            "limitations": assessment.get("limitations", []),
            "summary": assessment.get("summary", ""),
            "rationale": assessment.get("rationale", ""),
            "behavior": case.get("behavior", "unspecified"),
        })
    metrics = compute_metrics(results)
    payload = {
        "benchmark_version": "labeled-adr-evaluation-v1.0.0",
        "provider": args.provider,
        "score_algorithm": confidence.ALGORITHM_VERSION,
        "dataset_path": str(CASES_PATH.relative_to(ROOT)),
        "results": results,
        "metrics": metrics,
    }
    (out_dir / "evaluation.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(out_dir / "evaluation.md", args.provider, results, metrics)
    print(f"Evaluation complete: {len(results)} cases; three-way accuracy {metrics['exact_three_way_accuracy']:.1%}")
    print(f"Report: {out_dir / 'evaluation.md'}")
    print(f"Machine-readable results: {out_dir / 'evaluation.json'}")


if __name__ == "__main__":
    main()
