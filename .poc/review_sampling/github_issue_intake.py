#!/usr/bin/env python3
"""Build a review sample from a Pathfinder scope report and optionally open GitHub Issues.

Issues contain stable identifiers, versions, paths/locators, and hashes—not source
excerpts, prompts, or the full report. Use only with a repository whose visibility
and evidence-handling policy are appropriate for the event data.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from sample import build_batch, canonical


OUTCOME_MAP = {
    "deviation": "deviation",
    "aligned": "no_deviation",
    "uncertain": "inconclusive",
    "no_applicable_adr": "no_deviation",
}


def build_frame(report: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Create one review unit per event × ADR comparison; preserve no-match cases."""
    frame: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    catalog_hash = str(report.get("catalog_hash", ""))
    for result in report.get("results", []):
        event_id = str(result.get("event_id", "unknown"))
        comparisons = result.get("adr_matches") or []
        if not comparisons:
            comparisons = [{
                "adr_id": "NO-APPLICABLE-ADR",
                "adr_version": "n/a",
                "title": "No applicable ADR candidate",
                "comparison_result": result.get("comparison", {}).get("overall_result", "uncertain"),
                "requirement_evidence": {},
                "adr_source": {},
                "source_observations": [],
                "evidence_links": [],
                "candidate_explanation": result.get("scope", {}).get("reason", "No ADR comparison was produced."),
            }]
        for comparison in comparisons:
            adr_id = str(comparison.get("adr_id", "unknown"))
            unit_id = f"{event_id}:{adr_id}:{catalog_hash or 'catalog-unversioned'}"
            result_label = str(comparison.get("comparison_result", "uncertain"))
            sample_outcome = OUTCOME_MAP.get(result_label, "inconclusive")
            observations = comparison.get("source_observations", [])
            links = comparison.get("evidence_links", [])
            flags = []
            if sample_outcome == "inconclusive":
                flags.append("UNRESOLVED_COMPARISON")
            if not observations or not links:
                flags.append("LIMITED_EVIDENCE_LINKAGE")
            frame.append({
                "unit_id": unit_id,
                "outcome": sample_outcome,
                "evidence_band": "high" if observations and links else "low",
                "impact": "medium",
                "risk_flags": flags,
            })
            details[unit_id] = {
                "event_id": event_id,
                "event_summary": result.get("event_summary", ""),
                "overall_result": result.get("comparison", {}).get("overall_result", "uncertain"),
                "scope_disposition": result.get("scope", {}).get("disposition", "unknown"),
                "adr_id": adr_id,
                "adr_version": comparison.get("adr_version", "n/a"),
                "adr_title": comparison.get("title", "No applicable ADR candidate"),
                "comparison_result": result_label,
                "candidate_explanation": comparison.get("candidate_explanation", ""),
                "catalog_hash": catalog_hash,
                "requirement_evidence": comparison.get("requirement_evidence", {}),
                "adr_source": comparison.get("adr_source", {}),
                "source_observations": observations,
                "evidence_links": links,
                "control_limitations": comparison.get("control_limitations", ""),
            }
    return frame, details


def build_issue(unit_id: str, selected: dict[str, Any], detail: dict[str, Any],
                report_run_url: str) -> tuple[str, str]:
    safe_id = unit_id.replace(":", " · ")
    title = f"[Pathfinder review] {detail['comparison_result']} · {detail['adr_id']} · {detail['event_id']}"
    req = detail.get("requirement_evidence") or {}
    adr_source = detail.get("adr_source") or {}
    observations = detail.get("source_observations") or []
    links = detail.get("evidence_links") or []
    observation_lines = []
    for obs in observations:
        locator = f"{obs.get('path', 'unknown')}:{obs.get('line', '?')}"
        observation_lines.append(
            f"- `{obs.get('evidence_id', 'unknown')}` — `{locator}` "
            f"(excerpt SHA-256: `{obs.get('excerpt_sha256', 'unavailable')}`)"
        )
    link_lines = [
        f"- `{link.get('link_id', 'unknown')}`: requirement `{link.get('requirement_evidence_id', 'unknown')}` "
        f"{link.get('relationship', 'unknown')} observation `{link.get('observation_evidence_id', 'unknown')}`"
        for link in links
    ]
    body = f"""<!-- pathfinder-review-unit: {unit_id} -->

## Review context

This issue was generated from the Pathfinder ADR-scope comparison pipeline. The current intake workflow uses the repository's **synthetic offline fixtures and lexical/cue-rule baseline**. A deviation is a candidate for human review, not a production-quality conclusion.

- **Review unit:** `{unit_id}`
- **Analysis event:** `{detail['event_id']}`
- **Workflow run:** {report_run_url or 'not supplied'}
- **Event summary:** {detail['event_summary'] or 'not supplied'}
- **Scope disposition:** `{detail['scope_disposition']}`
- **Overall event result:** `{detail['overall_result']}`
- **ADR:** `{detail['adr_id']}` version `{detail['adr_version']}` — {detail['adr_title']}
- **Per-ADR comparison:** `{detail['comparison_result']}`
- **Review selection:** `{selected.get('selection_reason', 'unknown')}`
- **Evidence band:** `{selected.get('evidence_band', 'unknown')}`
- **Inclusion probability:** `{selected.get('inclusion_probability', 'not applicable')}`
- **Design weight:** `{selected.get('design_weight', 'not applicable')}`
- **Catalog SHA-256:** `{detail['catalog_hash'] or 'unavailable'}`

## Requirement provenance

- Requirement evidence ID: `{req.get('evidence_id', 'unavailable')}`
- ADR source path: `{adr_source.get('path', req.get('path', 'unavailable'))}`
- ADR source SHA-256: `{adr_source.get('sha256', req.get('source_sha256', 'unavailable'))}`
- Chunk ID: `{adr_source.get('chunk_id', req.get('artifact_id', 'unavailable'))}`

## Source evidence references

{chr(10).join(observation_lines) if observation_lines else '- No source observations were linked to this candidate.'}

## Requirement-to-observation links

{chr(10).join(link_lines) if link_lines else '- No typed evidence links were emitted for this candidate.'}

## Candidate explanation

{detail['candidate_explanation'] or 'No explanation was provided.'}

## Known limitations

{detail['control_limitations'] or 'The local baseline uses deterministic cue rules; verify the original requirement, source revision, and any missing counter-evidence.'}

The issue intentionally contains **references and hashes, not source excerpts or prompts**. Inspect the controlled source and workflow artifacts before deciding. Do not paste secrets, customer data, or confidential source text into comments.

## Reviewer response

Please comment using this structure:

```yaml
reviewer: "<GitHub handle or team>"
disposition: "confirmed_deviation | false_positive | aligned_confirmed | missed_deviation | inconclusive_correct | needs_more_evidence | cannot_review"
reason_code: "evidence_supports_claim | incorrect_adr | out_of_scope | valid_exception | incorrect_observation | invalid_inference | missing_counter_evidence | stale_or_wrong_locator | missing_runtime_evidence | conflicting_requirements | reviewer_disagreement | insufficient_context | other"
supporting_evidence_refs:
  - "EV-..."
counter_evidence_refs:
  - "EV-..."
rationale: "<what the evidence establishes, and what it does not>"
feedback_route: "applicability_retrieval | collector_provenance | evidence_retrieval | inference_evaluation | deterministic_guardrails | exception_lifecycle | runtime_evidence | policy_adjudication | other"
needs_adjudication: "yes | no | unsure"
```

A reviewer disposition is not an adjudication. Do not treat this issue as an automatic waiver, finding closure, or training signal. Only separately adjudicated, approved feedback can become an evaluation candidate; holdout cases must remain excluded.
"""
    return title, body


def prepare(report_path: Path, batch_path: Path, *, seed: str, per_stratum: int) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("scope report must contain a results list")
    frame, details = build_frame(report)
    batch = build_batch(frame, seed=seed, per_stratum=per_stratum, policy_version="github-issue-review-v1")
    selected_ids = {row["unit_id"] for row in batch.get("probability_sample", [])}
    selected_ids.update(row["unit_id"] for row in batch.get("risk_sample", []))
    missing = selected_ids - details.keys()
    if missing:
        raise ValueError("sample references unknown review units: " + ", ".join(sorted(missing)))
    batch["selected_review_units"] = sorted(selected_ids)
    batch["source_report_sha256"] = __import__("hashlib").sha256(report_path.read_bytes()).hexdigest()
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return batch, details


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--per-stratum", type=int, default=1)
    parser.add_argument("--run-url", default=os.environ.get("PATHFINDER_RUN_URL", ""))
    parser.add_argument("--render-only", action="store_true", help="write JSON issue payloads instead of creating issues")
    parser.add_argument("--payload-output", type=Path, default=None)
    args = parser.parse_args()
    batch, details = prepare(args.report, args.batch, seed=args.seed, per_stratum=args.per_stratum)
    probability = {row["unit_id"]: row for row in batch.get("probability_sample", [])}
    risk = {row["unit_id"]: row for row in batch.get("risk_sample", [])}
    selected_ids = batch["selected_review_units"]
    payloads = []
    for unit_id in selected_ids:
        selection = probability.get(unit_id, risk.get(unit_id, {"unit_id": unit_id, "selection_reason": "unknown"}))
        title, body = build_issue(unit_id, selection, details[unit_id], args.run_url)
        payloads.append({"unit_id": unit_id, "title": title, "body": body, "selection": selection})
    if args.render_only:
        if not args.payload_output:
            parser.error("--render-only requires --payload-output")
        args.payload_output.parent.mkdir(parents=True, exist_ok=True)
        args.payload_output.write_text(json.dumps(payloads, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Prepared {len(payloads)} review issue payload(s); none created.")
        return
    if not os.environ.get("GH_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        raise SystemExit("GH_TOKEN and GITHUB_REPOSITORY are required to create GitHub Issues")
    created = []
    for item in payloads:
        result = subprocess.run(
            ["gh", "issue", "create", "--repo", os.environ["GITHUB_REPOSITORY"],
             "--title", item["title"], "--body", item["body"]],
            check=True, capture_output=True, text=True,
        )
        created.append({"unit_id": item["unit_id"], "url": result.stdout.strip(),
                        "selection_reason": item["selection"].get("selection_reason")})
    print(json.dumps({"created_issue_count": len(created), "issues": created}, indent=2))


if __name__ == "__main__":
    main()
