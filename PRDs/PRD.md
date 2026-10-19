# Product Requirements Document: ADR Deviation Service

**Author:** Project team (owner TBD)  
**Status:** Draft for review  
**Last updated:** 2026-10-19  
**Decision status:** This PRD describes product requirements and proposed V1 scope. It does not convert repository recommendations or open questions into accepted architecture decisions.

For the AWS end-state product requirements, see [PRD: ADR Deviation Service — AWS Target Product](PRD_FINAL_PRODUCT.md).

## 1. Overview

### Problem statement

Engineering teams need to understand whether a proposed technical design or code change conflicts with the architecture decisions that apply to it. Today, reviewers must locate relevant ADRs, determine whether they are current and in scope, inspect source evidence, and explain the relationship manually. Similar wording is not enough: an irrelevant or superseded ADR must not be presented as a binding constraint, and absent evidence must not be reported as proof of alignment.

### Proposed solution

Provide an evidence-first analysis service, initially driven by GitHub Issues and Actions. A user supplies a technical specification, a small code sample, or a same-repository pull request. The service pins the submitted source version, identifies candidate applicable ADR requirements, extracts deterministic observations where supported, evaluates typed requirements, and publishes a structured, reviewable report with exact evidence references and limitations.

The V1 prototype uses GitHub as its intake, orchestration, result-delivery, and audit backbone. The GitHub Pages site explains and prepares submissions; evaluation itself runs in GitHub Actions. The current prototype corpus is a stand-in for a future authoritative ADR source. Real enterprise ADR retrieval/storage integration is outside the current prototype boundary.

### Goals

- Let an engineer submit ordinary pasted Markdown/spec text or code without manually supplying predicate/subject fields.
- Support same-repository PR analysis for multi-file changes, pinning source evidence to the PR head revision.
- Report supported deviation, partial alignment, alignment where evidence supports it, not applicable, and inconclusive/insufficient evidence as distinct outcomes.
- Explain each finding with source version, location or exact passage, decision identity, applicability basis, and limitations.
- Make the evaluation reproducible from pinned input, catalog identity/hash, and engine version.
- Keep the deterministic analysis spine generic across ADR IDs; requirement kinds and collectors are reusable and versioned rather than branching on individual ADR identifiers.
- Keep results advisory and preserve human authority over architecture decisions and code changes.

### Success measures

The following are proposed measures. Numeric release thresholds require a representative, reviewed evaluation corpus and approval; the prototype must not claim production quality from synthetic fixtures alone.

- **Usability:** a user can submit pasted spec/code or a supported same-repo PR without constructing observations JSON.
- **Evidence validity:** every actionable finding resolves to supplied, version-matched evidence; invalid references are rejected or made inconclusive.
- **Applicability:** out-of-scope ADRs are explicitly excluded or unresolved and never counted as aligned.
- **Outcome quality:** on a labeled set, report per-class precision/recall and confusion for deviation, partial, aligned, not applicable, and inconclusive outcomes.
- **Reproducibility:** identical pinned inputs, catalog, policy, and engine version produce the same deterministic report fingerprint for deterministic stages.
- **Safety:** source bodies and credentials are not echoed into issue comments or logs; no AI-only merge blocking or automatic remediation occurs.
- **Operations:** GitHub workflow failures, skipped evidence, retries, and catalog/engine versions are visible to maintainers.

## 2. Context

### Users and needs

| User | Need |
|---|---|
| Engineer proposing a design or code change | Submit the material they already have and learn which applicable decisions may be affected. |
| Reviewer / tech lead | See concise outcomes, traceable evidence, applicability reasoning, uncertainty, and next steps. |
| Architecture owner | Maintain authoritative decisions and review exceptions without having AI mutate the source of truth. |
| Service maintainer | Operate bounded, reproducible GitHub workflows and diagnose failures without exposing source content. |

### Product context and current prototype

- Repository documentation describes a Go Pathfinder analysis path on GitHub Actions, with issue paste intake and same-repository PR changed-file intake.
- The issue interface supports technical-spec paste and one sample-code paste; multi-file code is provided through the PR adapter.
- The paste extractor is deterministic and intentionally partial. Unsupported or low-confidence extraction remains inconclusive; absence of a mention is not treated as a false observation.
- A default prototype catalog exists under `data/adr_catalog`; synthetic mode is opt-in. Reports identify catalog mode and manifest hash.
- The Pages site prepares a GitHub issue submission; it does not perform live analysis in the browser.
- Current prototype outcomes are advisory. Workflow execution, artifact, and ledger status are not equivalent to a production service SLA.
- The organization's intended production ADR source is described by the user as ADRs in Bedrock with PostgreSQL vector embeddings. This integration is future scope; current repository decisions indicate PostgreSQL as authoritative and vector retrieval as optional pending measured evaluation. The production source contract and migration/ingestion process remain open.

### Assumptions requiring validation

- The initial pilot can use public or synthetic content in the current public repository; proprietary source must not be submitted there.
- The prototype corpus is useful for workflow and contract development, but is not adjudicated evidence of enterprise semantic quality.
- GitHub issue/PR users have an appropriate repository role and workflow permissions.
- Real ADRs will have stable identity, lifecycle status, scope/applicability metadata, supersession links, and immutable versions or hashes available to the service.

## 3. Requirements

### User stories and acceptance criteria

#### US-1: Submit a pasted technical specification

As an engineer, I want to paste a Markdown technical specification into a GitHub issue so that I can receive an ADR alignment assessment without manually translating the text into service-specific predicates.

- **Given** a valid analysis issue containing a spec and required attestation, **when** the workflow processes it, **then** it pins the submitted content, runs supported extraction and evaluation, and publishes a structured result.
- **Given** an input containing unsupported statements or missing evidence, **when** extraction/evaluation completes, **then** those requirements remain explicitly inconclusive or unsupported rather than being inferred as compliant.
- **Given** an invalid, oversized, or unattested submission, **when** intake validates it, **then** evaluation fails closed and a safe error summary is published without echoing the full source.

#### US-2: Submit code directly or through a pull request

As an engineer, I want to paste a small code sample or link a same-repository PR so that the service can compare implementation evidence with applicable decisions.

- **Given** a supported single code sample, **when** the issue workflow runs, **then** it analyzes the provided bytes and retains precise source evidence where the collector supports it.
- **Given** a same-repository PR reference, **when** intake succeeds, **then** the evaluated package is pinned to the PR head SHA and contains changed text files within configured limits or records explicit skips.
- **Given** a fork/cross-repository PR, **when** intake runs, **then** it is denied without evaluating untrusted remote content.
- **Given** secret-bearing, binary, or oversized changed files, **when** the adapter processes the PR, **then** it skips or rejects them according to policy and records limitations without inventing observations.

#### US-3: Understand each result

As a reviewer, I want distinct outcome categories and traceable evidence so that I can tell a verified conflict from partial support, no observed conflict, or insufficient information.

- **Given** a supported conflict with applicable ADR and exact source evidence, **when** the result is published, **then** it identifies the decision version, source version/location, outcome, severity separately from confidence, and the rationale.
- **Given** only partial evidence, **when** the result is published, **then** partial alignment is not upgraded to full alignment.
- **Given** no adequate evidence, **when** the result is published, **then** it is inconclusive/insufficient evidence, not “no deviation.”
- **Given** a model proposes an unknown evidence ID or mismatched source version, **when** validation runs, **then** the finding is rejected or downgraded to inconclusive and is not published as a validated deviation.

#### US-4: Apply the right decisions

As an architecture owner, I want applicability determined before comparison so that a textually similar but irrelevant or superseded ADR does not create a false finding.

- **Given** a candidate ADR outside the package's scope or lifecycle eligibility, **when** applicability is evaluated, **then** it is marked `not_applicable` or unresolved and does not count as aligned.
- **Given** no active requirements apply, **when** aggregation completes, **then** the report says no applicable requirements were evaluated and does not report `all_aligned`.
- **Given** ambiguous scope, **when** applicability cannot be established, **then** the report identifies the missing applicability evidence and requires review or remains inconclusive.
- **Given** a catalog-backed evaluation, **when** its report is written, **then** it records catalog identity, mode, manifest hash/version, and engine version.

#### US-5: Operate and reproduce analysis on GitHub

As a service maintainer, I want bounded, auditable workflows and immutable input references so that failures can be diagnosed and successful results reproduced.

- **Given** a successful evaluation or validated failure, **when** the GitHub workflow completes, **then** it retains the defined report/comment artifacts and attempts a lean append-only job ledger record without storing full source bodies in that ledger.
- **Given** a ledger write failure after a user-visible result, **when** the workflow ends, **then** the comment and report artifacts remain available and the ledger failure is surfaced as a warning/failure signal.
- **Given** duplicate workflow delivery, **when** the same logical job is processed again, **then** duplicate side effects are bounded and report/job identities remain traceable.

### Functional requirements

1. **Input formats:** V1 accepts issue-form Markdown specification text and one code sample; a same-repository PR is the V1 multi-file path. Additional formats require explicit prioritization.
2. **Normalization:** the service converts supported inputs into a pinned evidence package with source identity, revision/hash, media type, and explicit extraction limitations.
3. **Extraction:** deterministic collectors emit only observations they can support. Requirement-kind logic must not branch on ADR IDs. Unsupported formats/kinds fail closed or remain inconclusive.
4. **Decision selection:** applicability uses lifecycle status and explicit scope metadata before requirement evaluation. Similarity may identify candidates but cannot alone prove applicability.
5. **Evaluation:** typed requirements and generic predicates are evaluated with deterministic rules where possible. Any AI assessment is bounded, schema-validated, and subordinate to application-side evidence validation.
6. **Outcomes:** represent outcome, severity, confidence/quality, applicability, and review status as separate dimensions. Preserve `not_applicable` and `inconclusive` as distinct from alignment.
7. **Evidence:** every actionable finding references exact source version and valid evidence location/span. Do not publish fabricated, stale, or unresolvable references.
8. **Reporting:** issue comments are concise and safe; detailed structured reports are downloadable workflow artifacts. Do not put full spec/code bodies in comments or lean job records.
9. **Catalog identity:** each report records catalog identity/mode/hash and the analysis engine/policy/schema versions needed to interpret it.
10. **GitHub workflow:** staged Actions jobs handle intake, normalization/observation completion, evaluation, publication, and lean job-ledger append with bounded retries and visible failure states.
11. **Security:** treat issue text, code, ADRs, retrieved content, and model output as untrusted data. Enforce payload/file limits, path deny-lists, authorization, output escaping, secret redaction, and source freshness checks.
12. **Human authority:** no automatic ADR edits, code commits, merge, production mutation, or AI-only merge blocking.
13. **Reproducibility:** canonicalize ordering where it affects fingerprints, prompts, and outputs; pin all evidence and policy/catalog versions.

### Non-functional requirements

- **Reliability:** bounded retries and deadlines for external calls; classified failures; duplicate delivery and retry exhaustion are visible. GitHub Actions are the V1 orchestration substrate, not a claim of exactly-once execution.
- **Cost:** model use, if enabled, must have per-call and cumulative per-job token/call/spend/deadline limits. Prototype deterministic extraction can run without model calls.
- **Privacy:** current public-repository workflow is limited to synthetic/public content. A private enterprise pilot requires an approved repository visibility, retention, and model data-processing policy.
- **Security:** least-privilege GitHub permissions, validated references, bounded parsers, prompt-injection resistance, no secrets in source artifacts/logs/prompts, and safe Markdown publication.
- **Maintainability:** Go owns the production evaluation path. Keep a functional deterministic core and isolate network, GitHub, storage, and model effects behind adapters.
- **Scale:** the requirement catalog may grow without per-ADR code paths. Runtime cost should scale with candidate decisions/requirements and bounded evidence, not with bespoke workflow count. Large-catalog retrieval and real-corpus latency/cost targets remain to be measured.
- **Accessibility:** issue forms, workflow comments, and Pages guidance should be understandable without color-only status cues and should link to definitions of outcomes and limitations.
- **Availability and latency:** no numeric SLA or analysis-time target is committed for V1; establish targets from pilot measurements and GitHub Actions constraints.

## 4. Proposed user flow and technical considerations

```text
Engineer
  ├─ GitHub Issue: paste spec and/or one code sample
  └─ Same-repository PR: submit changed files at a pinned head SHA
            ↓
GitHub Actions intake and validation
            ↓
Pinned evidence package → deterministic observation collectors
            ↓
Applicability selection → typed requirement evaluation
            ↓
Evidence validation and outcome aggregation
            ↓
Issue comment + downloadable report + lean job ledger
```

The Pages site is an instructional/submission-preparation surface. GitHub Actions remain responsible for live execution. The current prototype uses the Go Pathfinder runtime and a checked-in catalog. A future authoritative catalog adapter may retrieve ADR metadata/content from the organization's existing system, but source-of-truth ownership, PostgreSQL schema/embedding contract, synchronization, freshness, and retrieval evaluation must be decided before implementation.

The repository's current direction recommends Go, direct Anthropic API when model assessment is needed, PostgreSQL as authoritative data, and Step Functions as the recommended future cloud orchestration owner. These are not all deployed or fully approved production decisions. AWS is outside the present GitHub prototype scope. Protobuf is a proposed versioned contract; a production gRPC endpoint is not required by this GitHub Actions V1 and its hosting decision remains open.

## 5. Scope

### In scope for usable GitHub V1 prototype

- Issue-based submission of real user-provided public/synthetic Markdown and code samples.
- Same-repository PR changed-file intake for multi-file code, pinned to commit SHA.
- Go-based generic catalog evaluation with typed requirements and reusable predicate/collector kinds.
- Applicability filtering, explicit limitations, outcome distinction, evidence validation, and reproducible report metadata.
- GitHub Actions workflow stages for intake through publishing and lean job indexing.
- GitHub Pages documentation that accurately explains submission, normalization, analysis stages, result semantics, safety, and current limitations.
- A broad synthetic/prototype corpus for exercising domains, clearly labeled as unadjudicated and not an authoritative enterprise ADR corpus.
- Offline deterministic tests and labeled evaluation fixtures as release evidence; live provider testing only under approved data/cost controls.

### Out of scope for this V1

- Treating synthetic or prototype ADRs as the user's authoritative company decisions.
- Connecting to the organization's existing Bedrock/PostgreSQL vector store or migrating its ADRs.
- A production multi-tenant hosted API, production SLO, formal compliance certification, or enterprise-wide rollout.
- AWS deployment, Lambda/Step Functions implementation, or production gRPC listener.
- Broad support for every language, binary/document format, or arbitrary external repository.
- Automated remediation, ADR mutation, code changes, merge decisions, or model-only blocking.
- Claiming calibrated accuracy from fixture tests or unreviewed synthetic labels.

### Future considerations

- A versioned ADR ingestion/catalog adapter that treats source records as authoritative, preserves immutable versions, and records scope/status/supersession/owner metadata.
- Hybrid retrieval and PostgreSQL vector search only after recall/precision, freshness, and cost are evaluated against labeled applicable-decision cases.
- User-facing dispositions, waiver/exception workflow, and organizational policy for approving/expiring exceptions.
- Private GitHub organization pilot, stricter authorization/retention controls, and deployment profile selection.
- Additional formats and collectors prioritized from measured pilot misses, not one-off ADR IDs.
- Production service orchestration, API, and contract decisions through reviewed OpenSpec/ADR changes.

## 6. Delivery sequence and dependencies

No calendar dates are committed. Sequence is gated by review and evidence:

1. **Prototype readiness:** review this PRD, confirm user-visible outcomes, content policy, and the initial GitHub workflow contract.
2. **Reliable GitHub vertical slice:** verify issue paste, same-repository PR, pinning, bounded ingestion, artifacts/comments, ledger semantics, and failure behavior.
3. **Quality corpus:** review labels/evidence for representative domains; measure retrieval/applicability/evidence validity and false positives/negatives; define thresholds with stakeholders.
4. **Enterprise ADR source discovery:** document existing ADR lifecycle, IDs, metadata, PostgreSQL/vector schema, embedding model/version, access controls, and update events; select a source adapter and reconcile strategy.
5. **Controlled pilot:** use a private organization/repository, approved data handling, security review, retention policy, operating limits, and human review.
6. **Production decision:** approve API/workflow hosting, reliability targets, ownership, support, and any future AWS scope separately.

### Dependencies

- Stable input and report schemas with compatibility checks.
- Reviewed catalog lifecycle/applicability metadata and realistic labeled cases.
- GitHub workflow permissions and organization policy for issue/PR data.
- For proprietary source, explicit approval of model provider/data processing, retention, and egress.
- For production ADR integration, source-system access and a documented synchronization/versioning contract.
- For quality claims, architecture/security reviewer time to adjudicate representative cases.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Similarity retrieval selects irrelevant ADRs | Separate candidate retrieval from applicability; expose basis/uncertainty; benchmark recall and false inclusion. |
| Sparse input is reported as aligned | Keep inconclusive distinct; require positive evidence for supported outcomes. |
| Generic collectors miss domain-specific implementation evidence | State coverage/limitations; add reusable kinds only with reusable tests and evaluation evidence. |
| Prototype corpus is mistaken for company policy | Prominent corpus mode/hash and synthetic/unadjudicated label in reports and site documentation. |
| Public GitHub content exposes proprietary code | Attestation, documentation, same-repository controls, path/size filtering; require a private pilot for proprietary data. |
| Prompt injection or fabricated citations affect findings | Treat artifacts as untrusted; validate IDs, versions, authorization, and state transitions in Go before publication. |
| GitHub Actions retries create duplicate effects | Idempotent job identities, bounded retries, serialized ledger writes, and explicit at-least-once semantics. |
| Vector search is trusted without evidence | Compare against exact/metadata/full-text baselines on a labeled corpus before adopting as a decision dependency. |

## 7. Stakeholder review and open questions

| Stakeholder | Review focus | Sign-off status |
|---|---|---|
| Product / service owner | V1 user flow, outcomes, scope, success measures | Not recorded |
| Engineering | Go runtime, workflow stages, contracts, scale/reliability | Not recorded |
| Architecture owners | ADR applicability metadata, lifecycle, exceptions, corpus labels | Not recorded |
| Security / privacy | GitHub scopes, source handling, model egress, retention, prompt injection | Not recorded |
| QA / evaluation owner | Labeled corpus, scenario coverage, thresholds, release evidence | Not recorded |
| Legal / compliance | Applicable only if pilot data or policy requires it | Not recorded |

Open questions that need explicit decisions before a production pilot:

1. Which result vocabulary and severity policy should reviewers see, including “partial alignment” semantics?
2. Which ADR lifecycle states count as candidates, and how are exceptions, waivers, ownership, and supersession represented?
3. What is the authoritative ADR source API/schema, and how do PostgreSQL records, vector embeddings, versions, and refreshes relate?
4. Which data may be sent to the direct Anthropic API, under what retention and regional controls, and what is the approved fallback when AI is unavailable?
5. Which GitHub organization/repository and permission model will host private pilot submissions?
6. What evidence-quality, applicability, precision/recall, latency, and spend thresholds are required before users rely on results?
7. What retention period applies to issue bodies, pinned packages, workflow artifacts, model usage metadata, and reviewer feedback?
8. Which deterministic checks, if any, may eventually block a merge, and what override process is required?

## Appendix: requirements-to-proof outline

Before implementation changes, each behavior change must receive a focused OpenSpec proposal/spec/design/tasks review. These acceptance criteria map to proof categories; exact test names and thresholds belong in the reviewed OpenSpec/evaluation plan.

| Requirement area | Minimum proof |
|---|---|
| Issue paste and normalization | Golden fixtures for Markdown, Go/Python samples, malformed and oversized input; verify pinned hashes and no fabricated observations. |
| PR intake | Integration/fixture checks for head-SHA pinning, fork denial, denylisted paths, file/byte caps, and partial skips. |
| Generic requirement engine | Same kind/predicate across multiple ADR IDs yields identical logic; no ADR-ID branches; deterministic report fingerprint. |
| Applicability | Active/inactive, superseded, out-of-scope, ambiguous, and zero-applicable cases have distinct dispositions. |
| Findings/evidence | Exact source-version references resolve; stale, fabricated, mismatched, or unknown references cannot publish as validated findings. |
| Workflow/replay | Duplicate delivery, bounded retries, ledger race/failure, publish failure, and artifact retention scenarios. |
| Quality | Versioned labeled evaluation reports class-level precision/recall, applicability, evidence support, inconclusive behavior, and corpus provenance. |
| Security/privacy | Prompt injection, secret redaction, unauthorized PR/repo, Markdown escaping, payload limits, and no raw source in comments/lean ledger. |

