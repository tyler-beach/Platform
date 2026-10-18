#!/usr/bin/env python3
"""Render or create a GitHub Issue for human review of a validated demo run.

Only metadata and evidence references are posted. Raw source excerpts, prompts,
secrets, and complete evidence payloads are intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def render_issue(report: dict[str, Any], manifest: dict[str, Any], evidence: dict[str, Any],
                 model: dict[str, Any], validation: dict[str, Any], run_url: str) -> tuple[str, str]:
    run_id = str(report.get("run_id", "")).strip()
    attempt = str(report.get("run_attempt", "")).strip()
    if not run_id or not attempt:
        raise ValueError("report must include run_id and run_attempt")
    if report.get("status") != "passed" or validation.get("status") != "passed":
        raise ValueError("refusing to open a review issue for a run that did not pass validation")
    outcome = str(report.get("actual_outcome", model.get("candidate", {}).get("outcome", "unknown")))
    comparison = str(report.get("comparison", "unknown"))
    sample_case = str(report.get("sample_case", "unknown"))
    language = str(report.get("language", "not applicable"))
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("manifest artifacts must be a list")
    artifact_lines = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_lines.append(
            f"| {artifact.get('artifact_id', 'unknown')} | {artifact.get('role', 'unknown')} | "
            f"`{artifact.get('version', 'unavailable')}` |"
        )
    if not artifact_lines:
        artifact_lines = ["| none | unavailable | unavailable |"]
    evidence_items = evidence.get("items", [])
    if not isinstance(evidence_items, list):
        raise ValueError("evidence items must be a list")
    evidence_lines = []
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        locator = item.get("locator", {})
        if not isinstance(locator, dict):
            locator = {}
        evidence_lines.append(
            f"| {item.get('evidence_id', 'unknown')} | {item.get('evidence_type', 'unknown')} | "
            f"`{item.get('source_path', 'unavailable')}:{locator.get('line_start', '?')}` | "
            f"{item.get('source_integrity', 'see workflow artifact')} |"
        )
    if not evidence_lines:
        evidence_lines = ["| none | none | unavailable | unavailable |"]
    cited = model.get("candidate", {}).get("evidence_ids", [])
    checks = validation.get("checks", [])
    check_lines = [f"- [{'x' if item.get('passed') else ' '}] {item.get('name', 'unnamed check')}" for item in checks if isinstance(item, dict)]
    title = f"[Pathfinder review] {outcome} · {comparison} · run {run_id}"
    body = f"""<!-- pathfinder-review-v1; machine-generated context is immutable below -->

## Why this review was opened

Please verify whether the analysis outcome is justified by the pinned requirement and evidence. This demo currently uses synthetic fixtures and a deterministic mock model; it is not a production finding.

- **Analysis run:** {run_id} (attempt {attempt})
- **Workflow evidence:** {run_url}
- **Comparison:** `{comparison}`
- **Scenario:** `{sample_case}`
- **Language:** `{language}`
- **Outcome:** `{outcome}`
- **Validation:** `{validation.get('status', 'unknown')}`
- **Evidence count:** {report.get('evidence_item_count', len(evidence_items))}
- **Cited evidence IDs:** {', '.join(f'`{item}`' for item in cited) if cited else 'none'}

## Pinned artifact versions

| Artifact ID | Role | SHA-256/version |
|---|---|---|
{chr(10).join(artifact_lines)}

## Evidence references

| Evidence ID | Type | Source locator | Integrity |
|---|---|---|---|
{chr(10).join(evidence_lines)}

Source text and prompts are intentionally not copied into the issue. Open the linked workflow artifact to inspect the complete synthetic package. Do not paste secrets or confidential source excerpts into issue comments.

## Automated validation

{chr(10).join(check_lines) if check_lines else '- No validation checks were included in the report.'}

## Reviewer response

Please add a comment using the following fields. Do not edit the machine-generated context above; corrections belong in comments so the original packet remains traceable.

```yaml
reviewer: "<GitHub handle or team>"
disposition: "confirmed_deviation | false_positive | aligned_confirmed | missed_deviation | inconclusive_correct | needs_more_evidence | cannot_review"
reason_code: "evidence_supports_claim | incorrect_adr | out_of_scope | valid_exception | incorrect_observation | invalid_inference | missing_counter_evidence | stale_or_wrong_locator | missing_runtime_evidence | conflicting_requirements | reviewer_disagreement | insufficient_context | other"
evidence_refs:
  - "EV-..."
counter_evidence_refs:
  - "EV-..."
rationale: "<brief explanation grounded in the referenced evidence>"
feedback_route: "applicability_retrieval | collector_provenance | evidence_retrieval | inference_evaluation | deterministic_guardrails | exception_lifecycle | runtime_evidence | policy_adjudication | other"
needs_adjudication: true
```

## Guardrails

- A reviewer disposition is not automatically an adjudicated evaluation label.
- Do not infer runtime/deployment behavior from static evidence alone.
- A missing observation is not proof of compliance.
- This issue does not automatically close a finding, waive an ADR, or change the model/rules.
- Only separately adjudicated, approved feedback may become an evaluation-corpus candidate; holdout cases remain excluded.
"""
    return title, body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-data", type=Path, default=Path("run-data"))
    parser.add_argument("--run-url", default=os.environ.get("PATHFINDER_RUN_URL", ""))
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    root = args.run_data
    report = read_json(root / "functional-analysis-report.json")
    manifest = read_json(root / "input-manifest.json")
    evidence = read_json(root / "evidence-package.json")
    model = read_json(root / "mock-model-response.json")
    validation = read_json(root / "validation-result.json")
    title, body = render_issue(report, manifest, evidence, model, validation, args.run_url)
    if args.render_only:
        print(json.dumps({"title": title, "body": body}, ensure_ascii=False, indent=2))
        return
    if not os.environ.get("GH_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        raise SystemExit("GH_TOKEN and GITHUB_REPOSITORY are required to create an issue")
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", os.environ["GITHUB_REPOSITORY"], "--title", title, "--body", body],
        check=True, capture_output=True, text=True,
    )
    print(f"Created human review issue: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
