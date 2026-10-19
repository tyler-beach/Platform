const e=`# Baseline and end-to-end investigation gate

This checklist is the next engineering gate for the ADR Deviation Platform. It is deliberately separate from the public demo UI. A green synthetic harness is not proof of live model quality, and a merged commit is not proof that GitHub Pages deployed it.

## Gate 1 — Establish a reproducible baseline

Run from a clean checkout of \`main\`:

\`\`\`sh
npm ci
npm test
npm run build
python .poc/evaluation/evaluate.py --provider mock --output-dir /tmp/adr-evaluation
python .poc/evaluation/evaluate_adr_corpus.py --output-dir /tmp/adr-corpus-audit
\`\`\`

Record the commit SHA, Node/Python versions, command exit codes, dataset fingerprints, generated report paths, and any skipped checks. Do not replace a failed or unavailable check with an assumed pass.

For the standalone Pathfinder signal-flow explorer, verify the deployed route after Pages completes:
\`https://tyler-beach.github.io/Platform/pathfinder-flow/\`.
Confirm that its HTML and assets load under the repository base path, it renders in a clean browser session, and no existing app route or shared styles changed. The explorer is an isolated view; its synthetic evidence must remain clearly labeled.

## Gate 2 — One replayable investigation

Implement a single offline vertical slice around the invariant: **a session TTL must not exceed 10 minutes**. Keep fixtures synthetic.

Inputs:
- A pinned, accepted ADR revision containing the session-TTL constraint.
- A pinned technical specification or implementation diff.
- A source manifest with exact path/line or structured locator, content hash, and source revision.
- Explicit applicability facts, including ADR status and scope.

The investigation must:
1. Resolve applicability before contradiction analysis.
2. Collect deterministic supporting, contradicting, and unresolved evidence.
3. Produce a typed outcome: \`supported_deviation\`, \`no_deviation_found\`, or \`inconclusive\`.
4. Validate every evidence reference against the immutable evidence package; reject unknown IDs and stale versions.
5. Persist or serialize a canonical result containing input hashes, policy/parser versions, evidence IDs, outcome, rationale, and uncertainty.
6. Replay the same pinned inputs deterministically without silently consulting current source state.

Required golden cases:
- TTL above 10 minutes with direct, valid evidence → supported deviation.
- TTL at or below 10 minutes → no deviation found.
- A similarly worded but out-of-scope or superseded ADR → not applicable, not a deviation.
- Missing or conflicting TTL evidence → inconclusive.
- A model-proposed citation that is absent from the evidence package → validation failure, never a finding.

The offline mock provider may exercise the workflow, but its output must not be described as evidence of Anthropic model quality.

## Gate 3 — Evaluation integrity

- Keep the regression corpus and holdout split explicit; test code must not tune thresholds against holdout cases.
- Report results by scenario family and expected disposition, not only aggregate accuracy.
- Include evidence-reference validity, unsupported-claim rate, inconclusive behavior, applicability errors, and replay consistency.
- Keep human corrections separate from baseline labels until an independent adjudicator approves promotion.
- Record corpus version/hash and evaluator version in every report.
- Label the current corpus as synthetic and not independently adjudicated until that process has actually occurred.

## Gate 4 — Human review loop

Verify the full path: sampled comparison → GitHub Issue with evidence/provenance → reviewer disposition → independent adjudication → candidate regression case. A reviewer disposition alone must not alter authoritative ADRs, thresholds, holdout labels, or baseline expectations.

Check duplicate submissions, repeated workflow attempts, malformed/partial dispositions, stale evidence, and retry behavior. Every transition should be auditable and idempotent.

## Gate 5 — Pilot source adapter

Only after the offline vertical slice passes, add one narrow adapter for the first approved input source. It must return immutable source references and hashes, distinguish unavailable/stale content from empty content, and expose bounded errors/retries. Do not add production credentials, cloud infrastructure, or proprietary source payloads until the source, retention, and Anthropic data-handling questions are explicitly approved.

## Current verification record

As of this checklist's creation:
- The labeled async-boundary evaluation file contains 20 synthetic cases.
- The ADR corpus audit is a deterministic integrity/source-fixture audit, not semantic adjudication.
- The GitHub connector did not return CI status checks for the latest explorer merge commit. Deployment and browser verification remain **unverified** until checked directly.
- This document is a gate definition, not a claim that these commands or scenarios have already passed.
`;export{e as default};
