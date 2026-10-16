# Open questions

Resolve these when their answers affect security, behavior, data model, cost or runtime. A coding agent must not silently guess high-impact decisions.

## Product and policy
- Which formats are in scope first (Markdown, DOCX, PDF, OpenAPI, source, tickets)?
- Which outcome categories/severity model are useful to reviewers?
- Advisory-only pilot, or can any deterministic check block?
- How are waivers, exceptions and time-bounded exemptions approved and represented?

## Sources and integrations
- How are ADRs identified/statused/approved today?
- What counts as an authoritative technical specification and how is it versioned?
- First input: GitHub PR, submitted diff/document, or both?
- Which GitHub scopes and installation model can be used?

## Security/data handling
- What policy governs proprietary code sent directly to Anthropic?
- What tenancy boundary is required for the pilot?
- Retention for snapshots, transcripts, traces, findings and review feedback?
- Required IAM, secret management and network egress constraints?

## Runtime and spend
- Go toolchain/version and IaC standard?
- Synchronous result or asynchronous job API?
- Latency, per-job cost, concurrency and monthly spend limits?
- What DB connection-management approach is needed under Lambda concurrency?

## Quality
- Which target languages first?
- Who labels/reviews the initial evaluation corpus?
- What measured precision/recall/evidence-validity threshold is required before gating?
- Which cases justify an independent model verification call?

## OpenSpec/engineering
- Which AI coding environments beyond Claude Code must be supported?
- Which CI, lint and security scanners are mandatory?
- Should the stock spec-driven OpenSpec schema remain, or is a custom schema warranted later?

## How to close a question
Record the answer, alternatives, trade-offs, owner and date. Behavior changes require a focused OpenSpec change. Cross-cutting or security-sensitive decisions should also be captured in a formal ADR.
