const e=`# Scope analysis to GitHub Issue review intake

This is the first end-to-end bridge from the ADR scope-comparison report into a GitHub Issue review queue. It is currently limited to the **offline synthetic scope scenarios** in \`.poc/scope/scenarios.jsonl\`; it is not yet connected to a production change-event source or deployed detector.

## Run locally without creating issues

\`\`\`sh
python .poc/scope/run_scope.py --output-dir /tmp/pathfinder-scope
python .poc/review_sampling/github_issue_intake.py \\
  --report /tmp/pathfinder-scope/scope-report.json \\
  --batch /tmp/pathfinder-scope/review-batch.json \\
  --seed local-pilot-01 --per-stratum 1 \\
  --render-only --payload-output /tmp/pathfinder-review-issues.json
\`\`\`

The intake maps each event × ADR comparison to a review unit. Events with no matched ADR still produce a separate \`NO-APPLICABLE-ADR\` unit so the review frame does not silently exclude retrieval misses. Outcomes map into the sampler's four categories; the issue retains the exact comparison result (including \`no_applicable_adr\`). The frame fingerprint, seed, per-stratum counts, inclusion probabilities, design weights, and risk queue remain in the batch manifest.

The probability sample is stratified by comparison outcome × evidence band. Risk-triage units are included separately and are not used in weighted population estimates. If a unit is selected by both mechanisms, one issue is created with probability-sample metadata taking precedence and the batch manifest preserves both lists.

## GitHub Actions

Run **Pathfinder Scope Review Intake** manually. It executes the offline scope simulation, creates a deterministic sample, and publishes the scope report, sample manifest, and rendered issue payloads as workflow artifacts. The \`create_issues\` input defaults to false. If enabled, it opens an issue for each selected review unit with a repository-scoped token.

The workflow uses synthetic fixtures only. It deliberately does not accept arbitrary source files or paste user-provided production source into public issue bodies. Before wiring a production event source, verify repository visibility, evidence access, retention, reviewer authorization, and the organization's policy for publishing evidence references.

## Issue contents and feedback

Issues preserve the event/run identifier, ADR revision, catalog hash, source path/line references, evidence IDs and hashes, typed relationship links, sampling reason, inclusion probability and design weight. They do not copy source excerpts or model prompts. Reviewers comment with the controlled disposition, reason code, evidence refs, rationale, feedback route, and adjudication request.

A reviewer comment is not a validated ledger event. The existing append-only ledger and adjudicated-feedback exporter remain the controlled path for evaluation-corpus candidates. This intake does not auto-close findings, waive ADRs, change enforcement, or train a model.
`;export{e as default};
