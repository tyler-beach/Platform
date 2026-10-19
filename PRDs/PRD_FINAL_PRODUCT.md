# Product Requirements Document: ADR Deviation Service — AWS Target Product

**Author:** Project team (owner TBD)  
**Status:** Draft for product, architecture, security, and operations review  
**Last updated:** 2026-10-19  
**Audience:** Product owner, engineering, architecture, security/privacy, operations, and pilot stakeholders  
**Decision status:** This document defines a target product and proposed requirements. It is not approval to deploy AWS infrastructure, send proprietary data to a model provider, or enable enforcement.

**Planning assumption:** This is the intended internal engineering product for an organization of roughly 15,000 employees and 2,000 engineers. Those figures describe organizational reach, not a concurrency, throughput, or SLA commitment. Where implementation choices remain open, this PRD selects a recommended product direction and records the assumption for owner review.

## 1. Executive summary

The ADR Deviation Service helps engineering teams determine whether a proposed technical specification or implementation is consistent with the architecture decisions that govern it. It accepts source material from GitHub and supported document/code inputs, discovers candidate ADRs from the organization’s authoritative decision corpus, establishes applicability, gathers source-versioned evidence, and returns a reviewable assessment with traceable rationale and uncertainty.

The finished product is an asynchronous, multi-workspace AWS service integrated with GitHub and directly callable from engineering systems. The target external integration is a versioned HTTPS JSON API fronted by API Gateway with AWS IAM authorization: engineering services obtain short-lived AWS credentials through their normal identity federation, sign requests with SigV4, and receive route-scoped `execute-api:Invoke` permission. This lets teams call the service from CI/CD, internal developer platforms, release workflows, and service-owned automation without sharing static API keys. GitHub webhooks use their own signed webhook boundary and are not required to sign AWS requests.

The API is a thin synchronous control plane for job submission and reads; a separate workflow plane performs analysis asynchronously. Go owns deterministic policy, evidence validation, and worker logic. The target workflow owner is Step Functions, invoking bounded Go Lambda workers. PostgreSQL/Aurora PostgreSQL stores authoritative job, decision metadata, provenance, findings, budgets, reviews, and audit records; S3 stores immutable large artifacts when required. Protobuf remains useful for versioned internal contracts and generated Go types. A public gRPC server is not the default integration surface in this PRD; add one only if a named consumer requires it and the operating trade-off is approved.

The product is expected to integrate with the company’s existing ADR corpus and PostgreSQL vector retrieval. The working assumption is that PostgreSQL stores authoritative ADR records/metadata and pgvector stores derived embeddings; the role of Bedrock in the existing ingestion or embedding pipeline must be confirmed. The repository’s current assessment-provider direction is direct Anthropic API, not Bedrock inference; this is separate from the existing ADR embedding flow. Proprietary source may be sent to a model only after security, privacy, legal, and data-processing approval.

The product is decision support. It does not authoritatively decide whether an architecture exception is acceptable, rewrite ADRs, commit code, merge changes, or block pull requests based solely on AI output. Findings are tied to exact source versions and distinguish deviation, partial alignment, supported alignment, not applicable, and inconclusive/insufficient evidence.

## 2. Problem and opportunity

Organizations with many teams and a large, changing ADR corpus cannot reliably depend on every engineer and reviewer to locate all applicable decisions and compare them manually against every design and implementation. Keyword search alone returns irrelevant or superseded decisions, while a simple pass/fail check can mistake missing evidence for compliance. AI-only review can produce unsupported or stale claims unless the system proves applicability and validates every cited source.

The service makes this review faster and more consistent by combining authoritative decision metadata, deterministic source analysis, bounded semantic assessment, and human review. It gives teams a reusable flow for new ADRs: add or update decision content and metadata in the source catalog; generic retrieval, requirement kinds, collectors, and evaluators handle it without creating a bespoke workflow for every ADR. New reusable predicate or collector capabilities may still be required when a decision asks for evidence the platform cannot currently observe.

## 3. Product vision and principles

### Vision

Make architecture decision adherence review a normal, evidence-backed part of engineering change review, with the decision corpus remaining the authoritative policy source and human owners retaining governance authority.

### Product principles

1. Applicability before deviation assessment.
2. Exact source-version evidence before explanation.
3. Missing or stale evidence means unknown, not compliant.
4. Generic requirement and predicate handling; no code branches keyed to ADR IDs.
5. Deterministic checks first; AI only for bounded judgments that benefit from semantic interpretation.
6. Model output is untrusted until validated by Go application policy.
7. Historical reports remain reproducible when source decisions later change.
8. Least privilege and least data; no unrestricted model tools or source mutation.
9. Human review for uncertain or consequential decisions.
10. Reusable stages and explicit contracts; no monolithic analysis service or competing workflow owners.

## 4. Users, jobs, and value

| Persona | Job to be done | Product value |
|---|---|---|
| Engineer / design author | Check a design or code change against governing decisions early | Find relevant constraints and evidence gaps before review stalls. |
| Pull request reviewer | Triage evidence-backed potential conflicts | See concise findings linked to exact source and applicable decision versions. |
| Architecture decision owner | Maintain decision scope, lifecycle, supersession, and exceptions | See where decisions are relevant and gather review feedback without surrendering authority. |
| Engineering manager / platform lead | Understand recurring policy gaps and adoption | See governed aggregate measures without treating raw AI outcomes as compliance scores. |
| Service operator | Keep job execution secure, bounded, available, and recoverable | Reconcile dispatch, diagnose failure stages, control spend, and audit access. |
| Security/privacy administrator | Control access, data handling, model egress, and retention | Enforce workspace boundaries and approved processing policy. |

## 5. Goals, non-goals, and success measures

### Goals

- Analyze implementation changes, technical specifications, and—when selected—specification-to-implementation alignment.
- Retrieve candidate ADRs at enterprise scale using authoritative metadata and measured retrieval methods.
- Establish decision status and applicability using scope, ownership, service/repository relationships, environment, time, exceptions, and supersession.
- Normalize heterogeneous input into immutable, versioned artifacts with source locators and hashes.
- Produce typed outcomes and individually traceable findings with supporting and contradictory evidence.
- Provide GitHub-native submission and review, plus a stable API for other authorized clients.
- Let engineering teams directly integrate through SigV4-signed requests using short-lived federated AWS credentials, with usable examples and scoped IAM policies.
- Offer asynchronous completion notification for AWS-native consumers without requiring every team to poll continuously.
- Provide an authenticated dashboard for adoption, analysis usage, deviation/alignment outcomes, evidence completeness, and AI usage/spend, with governed filters and export.
- Support multiple workspaces/repositories with explicit authorization and auditable isolation.
- Operate asynchronous analysis safely with idempotency, dispatch reconciliation, bounded retries, cancellation semantics, and per-job budgets.
- Learn from authorized human dispositions and labeled evaluation data without silently changing authoritative policy.

### Non-goals

- Replace ADR authorship, architecture review boards, exception governance, or source-control review.
- Guarantee a system is compliant simply because no deviation was found.
- Use vector similarity alone to decide applicability or normative authority.
- Automatically edit code/ADRs, approve exceptions, merge pull requests, or mutate production.
- Use model output alone to block a merge.
- Make every source format and programming language available at launch.
- Depend on an autonomous agent framework, long-term conversational memory, graph database, or a second orchestration engine without evidence and explicit approval.

### Success measures and release gates

Targets below are measures to establish, not invented numeric commitments. Product, security, and engineering owners must select thresholds from representative pilot baselines before a production launch.

| Measure | How it is measured | Release use |
|---|---|---|
| Applicable-decision recall/precision | Labeled retrieval set, stratified by domain and scope | Must meet approved minimums before relying on retrieved coverage. |
| Applicability correctness | Correct include/exclude/uncertain disposition against reviewed labels | Gate for any actionable finding and any later enforcement proposal. |
| Finding precision/recall | Human-adjudicated outcomes by outcome/severity/domain | Advisory quality and future policy decisions. |
| Evidence validity | Percentage of cited IDs, versions, and locations that resolve and support the claim | Invalid references are a hard publication failure for actionable deviation. |
| Correct uncertainty | Rate of insufficient/ambiguous cases kept inconclusive instead of asserted aligned/deviant | Safety gate; monitor by input type and domain. |
| Reviewer utility | Agreement, accepted/dismissed/deferred disposition, time-to-triage | Determines whether results materially help review. |
| Operational reliability | Job completion, dispatch age, stage failures, duplicate effects, recovery success | Service readiness and incident response. |
| Cost and latency | p50/p95 by stage and end-to-end; calls/tokens/spend per job and tenant | Configure quotas and service tiers from pilot evidence. |
| Security/privacy | Authorization, isolation, redaction, injection, retention, and audit test results | No launch with unresolved critical findings. |
| Developer integration | Time and success rate to make a first authenticated request and consume a completed result | Required for adoption beyond the built-in GitHub path. |
| Integration operations | Authenticated calls, IAM denials, throttles, idempotency conflicts, accepted jobs, and completion events by registered integration | Used for onboarding, capacity, abuse detection, and support; never log source content. |
| Dashboard utility | Dashboard use, filter/export success, data freshness, and agreement between aggregates and source job/finding records | Confirms that displayed operational and outcome measures are trustworthy and useful. |

No quality target should be claimed from the synthetic prototype corpus alone. Evaluation labels used for launch gates must have documented provenance, reviewers, adjudication, and version history.

## 6. Product scope

### Target launch scope

- Authenticated multi-workspace service and GitHub App or organization-approved integration.
- Direct engineering-team integration through a versioned HTTPS JSON API with API Gateway IAM authorization and SigV4 request signing.
- Documented short-lived credential patterns for AWS-hosted workloads and GitHub Actions OIDC; no long-lived shared API secrets.
- Async completion delivery for approved AWS consumers, initially through EventBridge or a documented polling contract, selected according to pilot needs.
- Developer onboarding package: OpenAPI contract, least-privilege IAM examples, curl/CLI example, Go example, GitHub Actions workflow example, idempotency and error guidance.
- GitHub pull-request change analysis pinned to immutable base/head revisions; GitHub issue/spec submission may be supported as a distinct entry path.
- API job creation, status, cancellation request, finding listing, and authorized finding detail.
- At least the three comparison modes: implementation ↔ ADR, specification ↔ ADR, and specification ↔ implementation, delivered only when the corresponding input and evidence adapter is supported.
- Versioned source and normalized artifacts, a generic requirement registry, reusable typed predicate/collector kinds, and an auditable catalog adapter.
- Candidate retrieval using exact identity, metadata/relationships, identifiers, full-text, then optional vector search validated by evaluation.
- Deterministic evidence collection plus a bounded direct Anthropic assessment adapter if provider/data policy approves it.
- Evidence validation, outcome aggregation, review queues/dispositions, idempotent GitHub publication, and audit trace.
- Operations console or documented operator APIs/runbooks for job lookup, reconciliation, replay, budget controls, and incident investigation.
- Authenticated product dashboard for workspace-scoped usage trends, analysis and outcome counts, outcome rates with explicit denominators, evidence/inconclusive coverage, and model token/call/spend reporting.
- Production security controls, retention, backup/restore, alerting, deployment/rollback, evaluation gates, and an approved support model.

### Explicitly staged scope

The full vision is not a single launch gate. A controlled launch can stage features:

1. **Internal shadow:** one organization/workspace, advisory-only, approved repositories and data policy, no merge blocking.
2. **Controlled pilot:** broaden users/domains/input types after retrieval and evidence quality review; capture human dispositions.
3. **General availability candidate:** approved availability, support, cost, retention, and recovery targets; multiple teams/workspaces; formal security/privacy sign-off.
4. **Optional enforcement evaluation:** only deterministic, narrowly scoped checks after governance approves thresholds, overrides, freshness, failure-open/closed behavior, and rollback. AI-only blocking remains disabled unless a separate approved policy explicitly changes this guardrail.

### Out of scope absent separate approval

- Building or deploying AWS infrastructure as part of writing this PRD; the target product itself is explicitly an AWS service.
- Automatic remediation or writes to source repositories/ADRs.
- Broad internet-wide repository access or arbitrary user-supplied source URLs.
- Unreviewed company-wide compliance scoring or employee performance analytics.
- Full automatic ingestion of all company documents without source ownership and access controls.
- Any claim of certification or regulatory compliance by using the service.

## 7. Core user journeys

### Journey A: PR review

1. An engineer opens or updates a supported pull request in an installed, authorized repository.
2. The integration receives a webhook, authenticates it, deduplicates the delivery, authorizes repository/workspace scope, and pins base/head SHAs.
3. The service accepts the job idempotently and returns a job reference quickly; analysis runs asynchronously.
4. Intake fetches only permitted changed files, applies file/count/byte/path policies, and records every skipped source as a limitation.
5. Normalization and deterministic collectors create versioned observations and source-located evidence.
6. Retrieval identifies candidate decisions, then applicability policy evaluates lifecycle and scope before comparison.
7. Deterministic rules run; a bounded model assessment is invoked only if permitted and useful within remaining budget.
8. Go validates model output, evidence IDs/versions, applicability, state transitions, policy, and freshness.
9. The service persists findings and usage/audit records. It publishes a concise idempotent PR check/comment according to workspace policy.
10. Reviewers can inspect authorized evidence, mark findings accepted/dismissed/deferred, and provide rationale tied to the finding version.

### Journey B: Technical specification review

1. An authorized user submits Markdown or a supported document through GitHub issue flow or API, with workspace/repository context and data classification.
2. The service pins content hash and source version, extracts atomic requirements while preserving modality and ambiguity, and identifies applicable ADR candidates.
3. The service compares requirement evidence to ADR constraints and returns supported deviation, partial support/alignment, supported alignment, not applicable, or inconclusive as appropriate.
4. The user receives a result link/comment and can review exact passages, decision versions, missing information, and limitations.

### Journey C: Decision owner updates ADR

1. The owner publishes a new ADR or changes its status/scope/supersession metadata in the authoritative source.
2. An ingestion/indexing process records a new immutable version and provenance, updates derived indexes, and marks dependent retrieval snapshots/index versions.
3. New jobs use the new version. Historical reports retain their original decision versions; re-analysis creates a new job and comparison rather than rewriting history.
4. Evaluation detects missing or malformed applicability metadata and surfaces ingestion/catalog quality issues for owner action.

### Journey D: Operator recovers a job

1. An alert or operator lookup identifies a job stuck in dispatch, a failed stage, budget exhaustion, or a publication issue.
2. The operator sees stage attempts, classified errors, source/catalog/pipeline versions, safe usage metadata, and reconciliation state.
3. Authorized recovery retries/reconciles the same logical job with the original idempotency and budget semantics, or records a terminal operator action.
4. Every action is audited. Replay cannot bypass authorization, data freshness, or spending limits.

### Journey E: Engineering team integrates directly

1. A team administrator registers an integration/workspace and maps the team’s AWS account, role, repositories, and permitted operations. Access is approved through the organization’s normal identity/IAM process.
2. A workload obtains short-lived credentials through an approved federation path, such as its AWS execution role or GitHub Actions OIDC role assumption. It does not store a shared static service token.
3. The workload sends HTTPS JSON to the versioned service API and signs the request with SigV4 for the configured AWS Region and API Gateway service. IAM policy limits the caller to the required API routes and methods.
4. The service maps the authenticated AWS principal to an authorized workspace and enforces repository and artifact access server-side. A signed request proves caller identity; it does not by itself authorize arbitrary workspace IDs in the request body.
5. The client creates an analysis job with an idempotency key and immutable GitHub revision or registered artifact reference. The API returns an accepted response with a job ID and status URL after durable acceptance.
6. The client polls status with bounded backoff or consumes a configured AWS completion event. It retrieves validated findings using the same authorization boundary and handles terminal failures distinctly from inconclusive findings.
7. The team can integrate this result into its own CI/CD or review flow. The service’s result is advisory unless a separate approved policy says otherwise.

### Journey F: Engineering lead monitors adoption and outcomes

1. An authorized engineering or architecture lead opens the dashboard for a workspace or organization scope they are permitted to view.
2. They select a time window and supported dimensions such as repository/service, domain, input type, integration, and outcome; every chart shows its population, denominator, and data freshness.
3. They compare analysis volume, deviation/partial-alignment/supported-alignment/inconclusive counts and trends, review dispositions, processing completeness, and AI call/token/spend usage.
4. They drill into authorized reports for context. The dashboard does not label teams or individuals as compliant, rank engineer performance, or treat an outcome ratio as a compliance score.

## 8. Functional requirements

### 8.1 Identity, workspace, and authorization

1. The service MUST authenticate every human, GitHub installation, webhook, service client, and operator action.
2. The service MUST authorize workspace, repository, source artifact, job, finding, evidence detail, cancellation, review, and publication actions on the server for every request.
3. Caller-supplied workspace IDs, repository names, paths, source URIs, artifact IDs, and page tokens MUST be treated as selectors, never as grants.
4. Tenant/workspace isolation MUST be enforced in persistence queries, object keys, caches, retrieval, logs, and workflow references.
5. The product MUST support least-privilege GitHub permissions and provide installation/removal and permission-change behavior.
6. Unauthorized-resource responses MUST not disclose whether another workspace's resource exists.

### 8.2 Source and ADR catalog

1. The service MUST identify an authoritative source of decision content and metadata per workspace or organization.
2. Each decision MUST have stable identity, immutable version/hash, lifecycle status, owner, scope/applicability metadata, effective dates when used, and supersession/relationship data where applicable. Missing critical metadata MUST be visible and may force uncertain applicability.
3. Ingestion MUST retain source URI/ID, version, content hash, retrieval timestamp, parser/normalizer version, and precise original-source locators.
4. Ingestion MUST be idempotent and reconcile missed/duplicate events; derived indexes MUST be rebuildable from authoritative source versions.
5. Decision status/scope changes MUST affect new analyses according to effective policy without rewriting historical report context.
6. Vector embeddings, if present, MUST be derived indexes with provider/model/version, content version, chunking method, and index build identity; they MUST NOT become the sole authority for source text or applicability.
7. Retrieval MUST apply authorization, status, scope, owner/service/environment/time, and relationship filters before normative assessment. Similarity alone MUST NOT establish applicability.
8. The source contract MUST support reconciliation against the existing company ADR system. Whether the source of truth is PostgreSQL, a Bedrock-backed pipeline, another API, or a combination MUST be confirmed before adapter implementation.

### 8.3 Input, normalization, and evidence collection

1. The service MUST accept only explicitly supported input types and expose size, count, archive/decompression, parse-time, and encoding limits.
2. Each artifact MUST be pinned to an immutable revision, content hash, or stable external version before analysis.
3. Normalization MUST preserve mapping from normalized chunks back to original paths, lines, symbols, sections, or document anchors, including locator precision.
4. Collectors MUST produce observations only when the source supports them; every observation records collector/kind/version, source evidence, confidence/quality where relevant, and limitations.
5. Unsupported formats, languages, constructs, and failed optional branches MUST be recorded. Required collection failure MUST produce an incomplete/inconclusive job outcome, not an assumed absence.
6. Multi-file processing MUST use bounded batches and concurrency; it MUST NOT create an unbounded worker invocation per file or per model reasoning step.
7. Collector and predicate behavior MUST depend on versioned kinds and predicate configuration, never on ADR identifier-specific code paths.

### 8.4 Retrieval, applicability, and comparison

1. Retrieval MUST record candidate set, source catalog version/index version, retrieval method/version, query context, scores where applicable, and exclusions/limitations sufficient for reproducibility.
2. Candidate retrieval MUST support exact IDs and explicit relationships, metadata/scope filters, identifiers/symbols/paths, full-text, and optional semantic retrieval when measured valuable.
3. Applicability MUST be evaluated separately from semantic similarity and before deviation judgment.
4. Applicability results MUST distinguish applicable, not applicable, and unresolved/unknown, with the rule/version and supporting metadata references.
5. The platform MUST support distinct comparison modes: implementation-to-ADR, specification-to-ADR, and specification-to-implementation. Unsupported mode/input pairs MUST fail clearly rather than return empty-success results.
6. Evaluators MUST support generic typed requirements/predicates across ADR domains; adding an ADR with an already supported kind MUST require catalog data, not bespoke application flow.
7. New domain concepts that cannot be represented by existing kinds require a reviewed schema/registry change, generic collector/evaluator implementation, migration/compatibility plan, and evaluation evidence.

### 8.5 Assessment, validation, outcomes, and finding model

1. The service MUST distinguish job execution state from finding outcome and review state.
2. Finding outcomes MUST represent at minimum supported deviation, potential/partial alignment as explicitly defined, supported alignment/no deviation found, not applicable, and inconclusive/insufficient evidence. Exact names and semantics require product approval.
3. Severity/impact, confidence or evidence quality, applicability, outcome, and human review status MUST be separate fields.
4. A confirmed actionable deviation MUST cite applicable decision version and exact implementation/specification evidence; missing or contradictory evidence may downgrade or reject it.
5. The system MUST retain counter-evidence and conflicting decisions when relevant, and must not make absence of retrieved evidence equivalent to proof of compliance.
6. Model output MUST be schema-validated and semantically validated in Go. It MUST NOT create source IDs, evidence IDs, locations, status, scope, or authorization.
7. Invalid, fabricated, stale, cross-job, or unauthorized evidence references MUST be rejected or downgraded to inconclusive and MUST NOT publish as validated deviation.
8. The system MUST record pipeline, policy, schema, prompt, model/provider configuration, retrieval/index, collector, validator, and report versions required to interpret and reproduce the result.
9. Finding fingerprints MUST be versioned and deterministic; deduplication MUST NOT erase distinct evidence or historical assessment versions.

### 8.6 Human review and feedback

1. Workspace policy MUST define which findings require review before publication, which can be automatically shown as advisory, and which source types are permitted.
2. Reviewers MUST be able to inspect authorized source version, locator, bounded excerpt, integrity/freshness, applicability basis, supporting/contradicting role, and limitations.
3. Review dispositions MUST include at least accepted, dismissed, deferred/needs-more-information, and not-applicable/exception referral; final vocabulary requires product approval.
4. Every disposition MUST bind to the exact finding version and record actor, time, rationale, and any linked exception/decision.
5. Feedback MUST NOT automatically alter ADR text, policy, model weights, or future decisions. Any use for evaluation/training requires a governed, reviewable process.

### 8.7 API, GitHub UX, and publication

1. The service MUST expose versioned job creation, status, cancellation request, finding listing, and finding retrieval operations with stable errors and pagination.
2. Job creation MUST be asynchronous and idempotent. The same workspace/key/request returns the same logical job; reusing a key with a changed request returns a conflict.
3. The service MUST commit job, idempotency state, and durable dispatch intent before acknowledging acceptance.
4. GitHub checks/comments MUST be idempotently published, escaped, size-bounded, and limited to validated result summaries and safe links. Full source bodies and private prompts MUST not be echoed.
5. Publication MUST recheck source freshness and workspace policy; stale input must be labelled and may require re-analysis or review.
6. API and GitHub adapters MUST map to the same domain contracts and state transitions. REST, gRPC, and webhook boundaries MUST not create duplicate domain semantics.
7. API versioning MUST be contract-first. Protobuf field numbers/names are never reused; Buf lint/build/breaking checks and REST mapping checks gate changes.
8. The external team-integration surface MUST be HTTPS JSON with API Gateway IAM authorization and SigV4 as the default planning target. Protobuf remains available for typed internal contracts; a public gRPC server requires a named consumer and separate operating approval.

### 8.8 Direct engineering-team integration and SigV4

1. The product MUST provide a stable, versioned HTTPS JSON API that engineering teams can invoke from their own CI/CD, release, platform, and service automation.
2. The default AWS-native client authentication MUST use API Gateway IAM authorization and SigV4-signed requests with temporary credentials. Long-lived shared API keys or static AWS access keys MUST NOT be required or recommended.
3. The service MUST document credential acquisition for AWS workloads and GitHub Actions OIDC, including role trust, audience/subject constraints, least-privilege `execute-api:Invoke` policy, region/service signing configuration, and identity-provider rotation.
4. IAM permissions SHOULD be scoped by stage, HTTP method, and route. The service MUST separately authorize the resulting principal to a registered workspace and permitted repositories; a valid SigV4 signature is authentication, not workspace authorization.
5. The API MUST support idempotent asynchronous job creation, status retrieval, findings retrieval, and cancellation request with stable error and retry semantics.
6. Clients MUST identify requests with an idempotency key, API version, source revision/hash, comparison mode, workspace integration identity, and correlation/request ID.
7. The service MUST publish an OpenAPI contract and examples for AWS SDK/CLI or curl-compatible signing, Go, and GitHub Actions OIDC. Additional generated SDKs are prioritized from measured language demand.
8. The client contract MUST define payload limits and a safe upload/reference flow for inputs too large for inline JSON. Clients may reference only artifacts the service independently authorized and pinned; caller-provided S3 URIs are not grants.
9. The service MUST provide a documented polling strategy with `Retry-After` or equivalent guidance and terminal-state handling. It SHOULD provide EventBridge completion delivery for approved AWS-native consumers when operationally supported.
10. Integration errors MUST distinguish authentication failure, IAM denial, workspace authorization denial, malformed request, idempotency conflict, rate limit, budget exhaustion, dependency outage, and job-level terminal failure.
11. All direct API routes MUST require authentication. Health checks and public documentation MUST NOT expose job data, catalog content, or operational internals.
12. The service MUST apply route-level rate limits, per-workspace quotas, request-size caps, and abuse controls independent of IAM authentication.
13. If private network-only access is required, deployment MUST select a private REST API or another approved private ingress pattern. API Gateway HTTP APIs support IAM/SigV4 authorization but do not support API resource policies; cross-account and private-network restrictions MUST account for this. A default HTTP API may instead use a platform-account role that callers assume, if enterprise identity policy permits.
14. GitHub webhook ingress MUST remain a separate integration boundary using GitHub webhook signature validation and installation authorization; it MUST NOT weaken SigV4 requirements for direct engineering API routes.

### 8.9 Developer experience and integration lifecycle

1. A team MUST be able to request, receive, and revoke access through a documented self-service or approved platform workflow.
2. Onboarding MUST explain API versions, supported sources, safe input handling, IAM identity setup, workspace mapping, quotas, data classification, model-use policy, and support contact.
3. The service SHOULD provide a reusable GitHub Action/workflow and a small Go client/example that use standard AWS credential chains and SigV4 signing rather than bespoke credential storage.
4. API deprecation MUST include a published support window, migration guide, usage visibility, and notice to affected integration owners.
5. API usage, denied requests, quota consumption, job completion, and caller identity MUST be observable per integration without placing source contents in ordinary logs.
6. Integration owners MUST be able to disable an integration, revoke role access, and locate outstanding jobs associated with it.

### 8.10 Search, catalog operations, and administration

1. Authorized maintainers MUST be able to inspect source synchronization health, rejected/malformed ADR records, index freshness, catalog versions, and coverage gaps.
2. The product SHOULD expose why a decision was retrieved and why it was considered applicable or excluded.
3. Search and analysis MUST be reproducible against a pinned catalog/index snapshot; historical reports must not silently resolve to the latest decision.
4. Workspace administrators MUST configure approved repositories, source types, retention, model use, rate/concurrency budgets, publication behavior, and review rules within organization policy.
5. Administrative changes MUST be versioned and audited, with effective time and actor.

### 8.11 Product dashboard and usage analytics

1. The product MUST provide an authenticated dashboard for authorized engineers, reviewers, decision owners, workspace administrators, and service operators, with role- and workspace-scoped views.
2. The dashboard MUST show analysis volume and trends; outcome counts and rates for supported deviation, partial alignment, supported alignment/no deviation found, not applicable, and inconclusive; job completion/failure and evidence completeness; and human review dispositions. It MUST show counts alongside rates and define each denominator, exclusion, and aggregation rule.
3. Users MUST be able to filter by time range, workspace, repository/service, decision domain, input type, comparison mode, integration/caller, and job/finding outcome where authorized. Drill-down MUST preserve normal evidence authorization and source-version controls.
4. The dashboard MUST present AI activity and cost attribution, including provider/model, calls, input/output token usage when returned, retries, per-job and aggregate spend, budget consumption/denials, and usage-estimation status. It MUST distinguish provider-reported usage, calculated/estimated cost, and reconciled billed cost; no exact cost claim may be made when pricing or usage data is unavailable.
5. The dashboard MUST identify data freshness, partial/late telemetry, missing provider usage, and aggregation lag. Aggregates MUST reconcile to durable job, finding, review, and usage records over a documented window.
6. Workspace/organization summaries MUST NOT expose another workspace’s content or permit identification of an individual engineer’s performance. Small-group suppression or equivalent policy MUST be applied where aggregate filters could reveal sensitive activity.
7. The dashboard MUST allow authorized users to open a report/finding only after server-side authorization. Export, if enabled, MUST be role-controlled, audited, bounded, and honor the same filters, retention, and privacy rules.
8. Dashboard analytics are for product adoption, architecture governance, operational capacity, and cost management. Outcome counts or rates MUST NOT be represented as proof of compliance or used as employee performance rankings.

## 9. Outcome semantics (proposed for review)

The following definitions are candidate product semantics and need product/architecture sign-off before they become normative API enums:

- **Supported deviation:** applicable decision and source-backed evidence support a conflict.
- **Potential deviation:** a credible conflict is indicated but applicability, evidence precision, or source coverage is incomplete.
- **Partial alignment:** some requirements/evidence align, while one or more applicable constraints are contradicted, unverified, or unsupported. The report must identify each part; the aggregate must not hide conflicts.
- **Supported alignment / no deviation found:** available evidence supports the assessed constraints and no contradiction was found within declared coverage. This is not a guarantee of full compliance.
- **Not applicable:** decision/requirement is out of scope or lifecycle-ineligible under versioned policy. It is not an alignment result.
- **Inconclusive / insufficient evidence:** evidence, source freshness, applicability, parsing, or retrieval is insufficient to make a supported determination.
- **Execution failure:** the analysis could not complete due to a technical or policy error. This is a job state/error, not a finding outcome.

Aggregate result rules must preserve all per-requirement outcomes and completeness; “all aligned” is forbidden when zero applicable requirements were assessed or required evidence branches failed.

## 10. Target architecture and AWS product boundary

This section is a proposed realization of the product requirements, not a declaration that AWS has been selected or deployed.

**Working product assumption:** API Gateway HTTP API is the default external REST/JSON surface with `AWS_IAM` route authorization and SigV4. Callers use temporary credentials; cross-account callers assume a narrowly scoped role in the service account unless enterprise network requirements select a private REST API profile. This makes direct integration a supported product capability rather than an optional future possibility. Validate private-network and cross-account access during architecture approval.

```text
Engineering CI/CD / internal platform / GitHub Actions OIDC
          │ HTTPS JSON + SigV4 + temporary AWS credentials
          ├────────────────────────────────────────────┐
          ▼                                            │
API Gateway HTTP API (AWS_IAM routes)                   │
          │                                             │
GitHub App webhook ingress (HMAC/App auth) ─────────────┘ separate trust boundary
          │ transactional acceptance + durable dispatch intent
          ├──────────────► Aurora PostgreSQL (jobs, idempotency, catalog metadata,
          │                  findings, budgets, reviews, audit, dispatch records)
          ▼
Dispatcher / reconciler ─────► Step Functions (single async workflow owner)
                                      │ bounded task integrations
                                      ▼
                              Go Lambda workers
                    intake · normalize · retrieve · collect
                     assess · validate · persist · publish
                         │                         │
                         ├──► S3 immutable artifacts │──► Anthropic API (only if approved)
                         └──► PostgreSQL / pgvector └──► GitHub APIs / EventBridge

OpenTelemetry SDK instrumentation → approved Collector/OTLP pipeline → CloudWatch (working target);
dashboard reads governed product aggregates, not raw telemetry. Secrets Manager/KMS/IAM/network policy
```

### Proposed component responsibilities

- **Ingress/control plane:** authentication, authorization, validation, idempotency, rate/usage limits, durable acceptance, status/read/cancel operations.
- **Direct API:** API Gateway HTTP API with IAM authorization and SigV4; OpenAPI JSON contract, route-scoped invocation policies, and a principal-to-workspace authorization mapping.
- **GitHub ingress:** separate public webhook boundary with signature verification and GitHub App installation authorization; no public API route is unauthenticated.
- **Dispatcher/reconciler:** leases durable dispatch intent, starts Step Functions with stable identity, resolves ambiguous starts, and alerts on stuck intents.
- **Step Functions:** sole owner of distributed analysis sequencing, branching, retries, timeouts, cancellation coordination, and terminal workflow state.
- **Go Lambda workers:** small bounded stages with explicit versioned inputs/outputs; no gRPC listeners; no competing job state machine.
- **Aurora/PostgreSQL:** authoritative business state and relational decision metadata. Existing PostgreSQL/pgvector may be reused only after its tenant/security/schema/operational contract is verified.
- **S3:** immutable large source/evidence artifacts if size, retention, or cost warrants; encryption, object versioning/checksum, access boundary, lifecycle, and orphan cleanup are defined.
- **Model adapter:** direct Anthropic API per repository direction, behind a provider boundary with no unrestricted tools. If provider direction changes, it requires an explicit reviewed decision and re-evaluation.
- **GitHub adapter:** webhook validation, installation identity mapping, least-privilege reads/writes, PR checks/comments, source freshness, and idempotent publication.
- **Observability:** Go services and supported adapters use OpenTelemetry APIs/SDKs for traces, metrics, and structured logs, exported through an approved Collector/OTLP pipeline (CloudWatch is the working AWS target). Trace ingress → durable dispatch → workflow → worker stages → retrieval → model → validation → persistence → review/publication. Correlate with opaque job/trace identifiers; do not put source text, prompts, secrets, user identities, or unbounded IDs in telemetry attributes. Business audit and durable product-usage records remain separate from telemetry and are the source for dashboard aggregates.
- **AI usage and spend accounting:** capture provider/model and model-version identity, request purpose, prompt/schema versions, provider request ID where safe, input/output/cached token counts when returned, call/retry counts, latency, classified result, and budget reservation/settlement. Calculate spend using versioned price metadata and persist whether it is provider-reported, estimated, or reconciled. Reconcile delayed usage/billing data; do not assume failed/timed-out calls are free. Keep per-job cumulative limits authoritative even when telemetry is delayed or unavailable.
- **Dashboard and analytics pipeline:** build aggregates from durable, authorized job/finding/review/usage records using bounded, refreshable materialization. OTel supports service health and diagnosis; it is not the authoritative ledger for product analytics or provider spend.

### Asynchronous acceptance invariant

Writing a database job and starting a Step Functions execution is a dual write. The product MUST NOT promise exactly-once execution. It MUST commit job + idempotency + durable dispatch intent atomically in PostgreSQL, acknowledge only after commit, and reconcile workflow-start ambiguity using leases/fencing and deterministic execution identity where supported. Logical effects are at-least-once delivered but idempotent.

### API profile assumptions and alternatives

| Profile | Target topology | When to use |
|---|---|---|
| **Default direct integration** | API Gateway HTTP API + IAM `AWS_IAM` authorization + SigV4 + Go Lambda integration; OpenAPI JSON contract | Engineering teams call from AWS workloads, GitHub Actions, CI/CD, and internal platforms using temporary credentials. HTTP APIs do not support API resource policies. |
| **Private-network profile** | API Gateway private REST API with VPC endpoint/resource policies and IAM authorization, or another approved private ingress | Use when private endpoint or resource-policy network restrictions are mandatory. |
| **Long-lived gRPC profile** | HTTPS ALB + Go service on ECS/Fargate; Protobuf/gRPC; async work stays in Step Functions/Lambda | Add only if a named consumer needs gRPC or long-lived streaming and the operating cost is approved. |

The HTTP API/SigV4 profile is the PRD’s working target. It must be confirmed against private-network and cross-account requirements before infrastructure is committed. AWS documents that HTTP API routes can use IAM authorization with SigV4 and route-specific `execute-api` permission; it also documents that HTTP APIs do not support API resource policies. If private API resource policies are required, use the private REST API profile or an approved role-assumption pattern. A gRPC server is not hosted in Lambda.

### Direct API request and result contract

1. `POST /v1/workspaces/{workspaceId}/analysis-jobs` accepts comparison mode, source references or an authorized upload reference, repository/ref context, idempotency key, and requested policy profile. It returns `202 Accepted`, job ID, status URL, and request/correlation IDs only after the job and durable dispatch intent commit.
2. `GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}` returns execution state, safe progress stage, completeness, terminal error class, and result availability without exposing source text by default.
3. `GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}/findings` returns stable-paginated findings with outcome, severity, applicability, evidence quality, review state, source-version references, and safe locators.
4. `GET /v1/workspaces/{workspaceId}/findings/{findingId}` returns one authorized finding and evidence references allowed by caller policy.
5. `POST /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}:cancel` records a best-effort cancellation request.

These routes are a product-level starting contract and must be reconciled with `docs/openapi.yaml` and Protobuf before implementation. Large input handling uses a service-issued scoped upload session or authorized GitHub revision; arbitrary caller S3 URIs are not accepted as authorization. Polling is the baseline completion mechanism. EventBridge completion delivery is a target for AWS consumers when confirmed; delivery is at-least-once and consumers deduplicate by event/job version.

Illustrative request body (field names remain subject to the versioned API contract):

```json
{
  "comparisonMode": "IMPLEMENTATION_TO_ADR",
  "source": {
    "kind": "GITHUB_PULL_REQUEST",
    "repository": "engineering/payments-api",
    "baseRevision": "4a61…",
    "headRevision": "7f2c…",
    "pullRequestNumber": 482
  },
  "policyProfile": "advisory-default"
}
```

The client supplies `Idempotency-Key` and uses an AWS SDK credential provider chain to sign the HTTPS request for the configured API Gateway Region/service. The accepted response returns a job ID and status URL; it does not wait for analysis completion. A Go or other supported client must be able to make this call without custom static secrets or knowledge of internal workflow names. A successful API response means durable job acceptance, not successful analysis.

### Cross-account identity and authorization

Preferred workload identity is temporary credentials from the caller’s existing AWS role or approved federation, including GitHub OIDC for Actions. The onboarding guide provides narrowly scoped `execute-api:Invoke` policies. For cross-account use, the default assumption is that the consumer assumes an explicitly trusted role in the service account; that principal maps to registered workspace integrations. Static access keys are not a supported onboarding path. Role trust conditions, organization/account boundaries, workload subject constraints, and workspace mapping are enforced and audited.

## 11. Data, privacy, and retention requirements

### Data classes

The product handles GitHub identity and repository metadata, ADR/spec/code content, extracted observations, evidence excerpts, model requests/responses/usage, findings, reviewer feedback, and operational/audit records. Each class needs an owner, classification, permitted purpose, storage location, access policy, retention, deletion behavior, and model-egress rule.

### Requirements

1. The organization MUST classify each input and define whether it may be processed by the selected model provider, including no-send categories.
2. The service MUST minimize provider input to relevant excerpts and required context. Redaction must preserve provenance and record that content was redacted.
3. Secrets MUST NOT enter prompts, fixtures, logs, comments, traces, or evaluation corpora. Secret-like content must be detected/filtered according to approved policy.
4. Credentials MUST be held in approved secret-management services, rotated, scoped, and unavailable to the model.
5. At-rest encryption, TLS in transit, key ownership/rotation, backup encryption, and cross-region behavior require security approval.
6. Retention MUST be configurable by data class and workspace, including source snapshots, normalized artifacts, excerpts, model request/response metadata, usage records, findings, feedback, and audit events.
7. Deletion requests MUST define how primary records, S3 versions, derived indexes/embeddings, caches, backups, logs, and legal holds are handled and evidenced.
8. Raw source and full prompts/responses MUST be excluded from ordinary logs and metric dimensions. Controlled evidence access is audited.
9. Cross-workspace and cross-repository authorization MUST be tested on every API/read/write path, including evidence links, caches, replay, operator tools, and asynchronous callbacks.
10. The organization MUST confirm provider data use/retention terms and legal/privacy requirements before any proprietary content is sent externally.

## 12. Reliability, scaling, and operational requirements

### Job lifecycle

The product MUST define accepted, queued, running, needs-review, succeeded, failed, cancelled, and expired behavior, with allowed state transitions. Domain outcomes remain separate. Cancellation means a request to stop future work where possible; it cannot undo completed external effects. Retries use the original end-to-end deadline and cumulative budgets.

### External calls and retries

Every GitHub, database, object storage, workflow, and model call MUST have a deadline, bounded retry policy, classified errors, attempt identity, and telemetry. Do not retry authorization, malformed input, unsupported content, deterministic validation, or stale-source failures as transient faults. Retry-after guidance and rate limits are honored where applicable.

### Idempotency and replay

- Request identity binds workspace, caller key, and canonical request fingerprint.
- Stage identity binds job, immutable inputs, stage/pipeline/policy version, and operation identity.
- Finding identity and external publication identity are separate.
- Database constraints enforce uniqueness where practical; application checks alone are insufficient.
- Replay preserves original source/catalog/policy versions and cumulative budget; re-analysis under new versions is a new logical job.

### Fan-out and quotas

- Define required versus optional evidence branches and how incomplete branches affect results.
- Bound per-job file counts, batch size, concurrency, model calls, output size, total duration, total tokens/spend, and retries.
- Enforce workspace/tenant and global concurrency/rate caps.
- Reserve budget atomically or with serialized claims so parallel workers cannot each spend the full job cap.
- Keep Step Functions state small; pass identifiers, hashes, statuses, and bounded summaries rather than documents/diffs.
- Control database connection pressure under Lambda concurrency; select connection pooling/RDS Proxy based on load tests and operational cost.

### Availability and recovery

Before production, owners MUST set availability, RTO/RPO, maximum job age, backlog, recovery, and support targets. The system MUST have tested backup/restore, database migration rollback/expand-contract, artifact recovery, workflow reconciliation, safe replay, provider-outage behavior, and incident runbooks. No numeric SLO is committed in this draft.

### Observability and AI cost

OpenTelemetry is a target product requirement, not merely compatibility: instrument Go services and supported adapters with traces, metrics, and structured logs, then export through an approved Collector/OTLP pipeline. CloudWatch is the working AWS backend assumption; backend and retention remain subject to platform approval. Trace ingress → durable dispatch → workflow → worker stages → retrieval → model → validation → persistence → review/publication. Correlate by opaque job/trace identifiers. Record stage/attempt, duration, classified outcome, model/prompt/schema/catalog/policy versions, provider usage and cost status, retry count, evidence package identity, and validation results. Avoid raw source, prompts, secrets, personal identities, and unbounded/high-cardinality values in metric dimensions. Audit state transitions and access separately from telemetry.

AI usage is captured at the model adapter and persisted in the durable product ledger for per-job budgets and dashboard aggregation. Store provider-reported token usage where available; calculate spend from versioned provider/model price metadata and label it estimated until reconciled to provider billing. Expose calls, tokens by type when available, retries, estimated/reconciled spend, budget use, and missing/delayed metering. Telemetry export failure MUST NOT bypass budget enforcement or lose durable accounting. CloudWatch/OTel telemetry supports operational diagnosis; it is not the product analytics system of record.

The product dashboard presents usage and outcome trends from authorized durable aggregates, with counts, explicit denominators, filter scope, and freshness. It must avoid interpreting deviation/alignment ratios as compliance scores and must not enable individual employee performance ranking.

Required alert/runbook areas include stuck dispatch intent, workflow backlog/throttling, expired jobs, database saturation/migration errors, source/index freshness, provider outage/rate-limit/cost spikes, budget denials, invalid-output spikes, duplicate publication, and backup/restore.

## 13. Security and abuse requirements

- Treat all source artifacts, ADRs, retrieved passages, issues, code comments, model outputs, and feedback as untrusted data, never instructions.
- No model access to shell, arbitrary Git writes, AWS mutation, credentials, or unrestricted repository operations.
- Validate webhook signatures, OAuth/token audience, GitHub installation permissions, repository identity, API scopes, and every artifact dereference.
- Defend against prompt injection, poisoned ADR/retrieval content, fabricated citations, cross-tenant access, malicious archives/parsers, path traversal, denial-of-wallet, output injection, replay, and stale source.
- Apply least-privilege IAM, network egress restrictions, secret rotation, encryption, dependency scanning, static analysis, software provenance, and deployment approvals according to organizational policy.
- Escape Markdown/HTML; cap comments and API responses; return safe errors without source echo.
- Recheck authorization and freshness before reviewer access or publication.
- Security events and operator actions are auditable; alert channels do not contain source or secrets.

## 14. AI quality and model governance

1. Each model operation MUST have a named purpose, prompt/schema version, allowed input fields, output schema, per-call deadline, token/cost limit, error policy, and evaluation set.
2. A request preflight MUST account for system instructions, evidence, schemas/tools, content blocks, reserved output, and overhead. Estimation/counting method and version are recorded.
3. Per-job cumulative tokens, calls, retries, spend, and elapsed time MUST be bounded. Failed calls are treated as potentially billable until usage confirms otherwise.
4. Model/provider/model-version/prompt/schema/config identifiers and provider request IDs/usage metadata MUST be persisted where available.
5. Model response must pass structural and semantic validation. One bounded repair may be allowed only when explicitly configured and within budget; otherwise fail or return inconclusive.
6. Deterministic checks must run before asking a model to infer facts available directly from source.
7. Independent verification is selective, measured, and charged to the same budgets. Model-as-judge cannot be the only evaluator.
8. Prompt/model/retrieval/collector/finding-policy changes trigger versioned evaluation with before/after metrics and reviewed labels.
9. Model knowledge cannot add uncited organizational facts. All factual findings derive from the pinned evidence package.
10. Provider outage, refusal, timeout, malformed output, and budget exhaustion are explicit outcomes/errors, never “no deviation.”

## 15. Integrations and dependencies

### Required integrations

- GitHub App/API/webhooks for repository installation, PR events, changed-file retrieval, check/comment publishing, and issue/spec intake as approved.
- API Gateway IAM-authorized HTTPS API for direct engineering clients using SigV4 and temporary credentials; OpenAPI is the external contract and route IAM policies are part of onboarding.
- AWS STS/IAM federation and, where applicable, GitHub Actions OIDC for short-lived caller credentials and cross-account role assumption.
- Authoritative ADR catalog and decision lifecycle source, including exact-version reads and change detection.
- PostgreSQL/Aurora for durable business state and potentially the existing decision metadata/pgvector index.
- S3 where immutable artifact size/lifecycle requires it.
- Anthropic API for bounded assessment only after data processing and provider policy approval.
- AWS IAM, Secrets Manager, KMS, CloudWatch, and deployment/account controls selected by platform engineering.
- OpenTelemetry-compatible instrumentation and approved metric/trace/log backends.

### Conditional integrations

- Existing Bedrock-related ingestion or embedding pipeline: integrate only after clarifying whether Bedrock is used to generate embeddings, store/retrieve vectors, or perform model inference. This product’s repository direction currently says direct Anthropic inference, not Bedrock inference.
- Notifications beyond GitHub (email/chat): only after a concrete user need, consent model, and data-minimization review.
- Identity provider/SSO and enterprise authorization: required for production deployment; exact protocol/claims/group mapping are TBD.
- EventBridge completion events: provide for AWS-native consumers if the pilot validates the need; polling remains the initial required status contract.
- SQS: add only if measured buffering/backpressure need warrants it; do not add as default architecture decoration.

## 16. Rollout, migration, and support

### Rollout phases

1. **Design approval:** approve product boundaries, outcomes, source-system contract, threat model, data policy, API profile, and target proof plan.
2. **Infrastructure and integration foundation:** implement identity, durable job acceptance/reconciliation, GitHub integration, catalog adapter, artifact storage, observability, budgets, and security controls behind feature flags.
3. **Offline shadow evaluation:** run on approved fixtures and historical samples; do not publish to users until evidence and retrieval quality are reviewed.
4. **Internal advisory pilot:** limited repositories/users, advisory comments, no blocking, human disposition capture, incident/rollback coverage.
5. **Expanded controlled rollout:** add domains and formats based on measured gaps; review quality/cost/security and update limits.
6. **GA readiness review:** demonstrate quality thresholds, security/privacy approvals, SLO/DR, support ownership, migration/retention, and rollback.
7. **Enforcement proposal:** separate governance decision; deterministic-only candidates first, with explicit fail-open/closed and override policy. No implication of approval in this PRD.

### Existing ADR corpus integration / migration

The product should not require rewriting every historical ADR before the first integration. An ingestion and normalization adapter can preserve original content while building a versioned projection, then report metadata gaps. Before pilot use, each in-scope decision needs a stable source identity/version, lifecycle status, owner, scope/applicability, effective/supersession semantics, and links to service/repository/domain context sufficient for applicability. Missing fields should remain unknown and be routed for data remediation rather than guessed.

The migration plan must inventory current PostgreSQL tables, vector extension/index, embedding provider/model/version, chunking/normalization, metadata filters, authorization, freshness/update path, and backup/retention. The service should initially consume existing embeddings as a derived retrieval signal if their version/provenance and access model are adequate; otherwise build a parallel evaluated index without replacing the authoritative source. Re-embedding or schema changes require measured retrieval results, cost analysis, rollback, and a backfill/reconciliation strategy.

### Support model

Before production, name service owner, on-call/incident path, decision-catalog owner, evaluation/labeling owner, security/privacy contact, support hours, severity definitions, escalation targets, and customer/engineering communication path. The PRD does not invent an SLA or staffing commitment.

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| ADR metadata is inconsistent or too weak for applicability | Inventory and report metadata gaps; unknown stays unresolved; define owner and remediation process. |
| Retrieval misses governing decisions at corpus scale | Labeled retrieval benchmark, exact/metadata baselines, recall monitoring, pinned index versions, selective vector/reranker evaluation. |
| Similarity creates false normative applicability | Separate candidate retrieval from deterministic applicability policy and human review. |
| Sparse source input produces false assurance | Inconclusive-by-default for missing evidence; report coverage and tested scope. |
| Generic kinds cannot express a new decision | Versioned registry extension process with reusable collector/evaluator and cross-ADR fixtures; avoid per-ADR flows. |
| Model/provider receives prohibited proprietary content | Classification, egress allowlist, minimization/redaction, provider approval, no-send policy, audit. |
| Dual-write creates accepted jobs without workflows | Durable dispatch intent, leases/fencing, reconciler, alert/runbook, injected failure tests. |
| Retry/fan-out multiplies cost or duplicates effects | Atomic budget reservations, concurrency caps, idempotency constraints, bounded attempts, replay tests. |
| Tenant boundary leak through cache/object/evidence path | Authorization on every access, tenant-scoped keys/queries, isolation tests, audited operator access. |
| Human disposition is biased or labels are weak | Reviewer guidance, adjudication, provenance/versioning, measure agreement, avoid using unreviewed labels as ground truth. |
| gRPC profile adds cost without consumer value | Name actual synchronous gRPC consumer and compare serverless HTTP profile before selecting. |
| Prototype expectations are mistaken for production readiness | Clearly separate prototype artifacts from release criteria; require operational, security, and quality evidence. |

## 18. Acceptance and proof plan

The production product is not complete because a PRD, schema, diagram, or mock API exists. Each requirement needs an implementation and verification link. Minimum proof categories:

| Area | Required evidence before controlled production pilot |
|---|---|
| Authentication/authorization | Integration tests for workspace/repo/job/finding/evidence and operator scopes; negative cross-tenant tests. |
| Idempotent acceptance/dispatch | Transaction tests plus failure injection at DB commit, workflow start, timeout-after-start, reconciliation and fencing. |
| Source pinning/catalog | Immutable version/hash tests, status/scope/supersession scenarios, ingestion duplicates/gaps, stale-source behavior, catalog/index identity. |
| Retrieval | Versioned labeled corpus, recall/precision by domain/scope, zero-result and poisoned/irrelevant candidate cases. |
| Generic engine | Requirements with same kind under different ADR IDs produce identical rule behavior; no ADR-ID code branching; deterministic fingerprints. |
| Evidence | Fabricated/unknown/stale/cross-job refs, line mapping, excerpt digest/redaction, support and counter-evidence, exact source links. |
| Model harness | Request preflight, cumulative budget race, timeout/rate limit/refusal/malformed output, schema/evidence validation, provider usage reconciliation. |
| Security | Prompt injection, malicious parser/archive, secret exposure, output escaping, replay abuse, GitHub scope, egress and denial-of-wallet. |
| Review/publication | Idempotent check/comment, stale source, required review, disposition binding, publication failure, no source-body leakage. |
| Operations | Alerts/runbooks exercised for stuck dispatch, DB saturation, workflow/provider outage, replay, cancellation, backup/restore, migration rollback. |
| Quality | Independently reviewed labeled set; class-level metrics and uncertainty; approved thresholds; before/after regression evaluation. |
| API/contracts | Buf lint/build/breaking checks, OpenAPI validation/mapping, auth/error/pagination/idempotency behavior, old/new reader migration. |
| Product usability | Usability sessions with engineers/reviewers; submission success, comprehension of outcomes/limitations, review utility and time-to-triage. |

Tests and evaluations must run in layers: deterministic domain tests without live AWS/DB/provider; adapter/integration tests in isolated environments; resilience/security tests; labeled live-model evaluation only with approved credentials, data, budget, and reporting. Checks not run must be reported as not run.

## 19. Delivery sequence and dependencies

No delivery dates are set because team capacity, provider terms, source contracts, and AWS account readiness are unknown.

1. **Product decisions:** close the decision register below with named owners.
2. **Source discovery:** map the existing ADR lifecycle and PostgreSQL/vector/embedding data flow; select authoritative read contract.
3. **Contract and OpenSpec:** reconcile API, data, evidence, lifecycle, security, and product outcome semantics; approve focused behavior specs.
4. **Vertical slice:** one GitHub repository, one comparison mode, one source adapter, immutable evidence, generic evaluator, one bounded assessment operation, validated report, persisted job.
5. **Reliability/security foundation:** durable dispatch/reconciliation, authorization/isolation, budgets, retries, audit, retention, and failure injection.
6. **Quality and pilot:** representative labeled set, measured retrieval/evidence/outcome quality, internal advisory rollout, feedback and rollback.
7. **Scale domains and clients:** add reusable collectors, input formats, workspaces, and API clients only as evidence and owner capacity permit.
8. **Production readiness:** meet approved SLO, security/privacy, support, DR, cost, and evaluation gates.

Key dependencies include GitHub App ownership and permission approval, AWS account/network/IAM/platform standards, authoritative ADR catalog access, model provider/data-processing approval, PostgreSQL/vector operational ownership, security/privacy/legal review, evaluation annotators, service operators, and product/support ownership.

## 20. Decision register — outstanding items to make this PRD implementation-ready

These are the remaining product and architecture decisions that cannot be responsibly inferred from the current repository. Each needs an owner, options considered, chosen answer, rationale, date, and linked ADR/OpenSpec where it changes behavior.

### P0 — Required before production implementation/pilot

| ID | Decision | Recommended default for review | Owner needed |
|---|---|---|---|
| D1 | What is the authoritative ADR source and how does the reported Bedrock/PostgreSQL/vector setup work end-to-end? | Keep source text/metadata authoritative in the existing governed store; treat embeddings/index as derived; integrate read-only first. Confirm actual components before deciding. | ADR platform/data owner |
| D2 | What identity and tenancy boundary is used? | Map authenticated GitHub installations, human SSO identities, and SigV4 AWS principals to registered workspaces; reauthorize every operation. | Security/identity owner |
| D3 | Which input/comparison mode is the first production slice? | GitHub PR implementation ↔ ADR, then spec ↔ ADR; do not imply all modes at first launch. | Product + architecture |
| D4 | Which outcome vocabulary and aggregate rules are canonical? | Adopt the proposed distinctions in §9 and version enum semantics before API compatibility freezes. | Product + architecture |
| D5 | May proprietary source be sent to Anthropic, and under what data-processing/retention/region rules? | Default deny until written approval; offer deterministic/inconclusive path when model use is disallowed. | Security/privacy/legal |
| D6 | Which AWS API and network profile is required? | Target API Gateway HTTP API with IAM authorization and SigV4 for direct integrations; use short-lived federated credentials and a platform-account role assumption for cross-account clients. Select private REST API if private endpoint/resource-policy requirements demand it. A public gRPC service is not the default. | Platform architecture + security + API consumers |
| D7 | What initial data retention/deletion/backup policies apply by artifact class? | Separate configurable retention for source, excerpts, prompts/responses, reports, audit, usage, and derived embeddings. | Data governance/security |
| D8 | What cost, concurrency, latency, availability, RTO/RPO, and job-age ceilings are required? | Set through capacity/cost model and pilot baseline; configure, never hard-code assumptions. | Product + SRE/finance |
| D9 | What quality thresholds and human-review policy permit pilot/GA? | Advisory-only pilot; threshold numbers after independent labeling and baseline measurement. | Product + evaluation/security |
| D10 | How should waivers/exceptions be represented, approved, expired, and checked? | Keep exceptions authoritative and versioned in the decision system; unresolved waiver means review, not automatic suppression. | Architecture governance |
| D11 | Who owns service on-call, catalog quality, labeling/evaluation, and user support? | Named accountable owners and escalation routes before pilot. | Engineering leadership |
| D12 | What, if anything, can block merges later? | Keep AI-only blocking disabled; separately approve deterministic policy checks, freshness semantics, override, and fail-open/closed behavior. | Engineering governance |

### P1 — Required before broad rollout, can be deferred from first pilot with an explicit limitation

| ID | Decision | Owner needed |
|---|---|---|
| D13 | First supported languages/formats and parser/collector coverage | Product + engineering |
| D14 | Review and dashboard UX: GitHub check/comment only, web console, or both | Product + design |
| D15 | Cross-repository, monorepo, and shared-service applicability model | Architecture + GitHub platform |
| D16 | User-facing history/search and reviewer feedback visibility | Product + privacy |
| D17 | Embedding provider/model/chunking/version policy and reindex cadence, if existing vector index is reused | Data/ML platform |
| D18 | Multi-region or regional data residency requirements | Security/legal/platform |
| D19 | Availability tiers, planned maintenance, support hours, and incident communication | Product + SRE |
| D20 | Cost allocation/showback by workspace and model/indexing costs | Finance/platform |
| D21 | Should AWS clients receive completion through polling only, EventBridge, or both? | Product + platform |
| D22 | What SDKs/CLI/reusable GitHub Action are required at broad rollout? | Developer platform + product |
| D23 | Which roles can see organization/workspace dashboards, what aggregate suppression is required, and what refresh/export behavior is permitted? | Product + privacy/security |
| D24 | Which OTel Collector/exporter/backend and retention/cost controls are approved, and how will model-provider usage reconcile with billed spend? | SRE/observability + finance + AI platform |

## 21. Stakeholder review

| Stakeholder | Required review | Status |
|---|---|---|
| Product owner | Personas, outcomes, first slice, success measures, rollout | Not recorded |
| Architecture governance | ADR lifecycle/applicability, exceptions, comparison semantics | Not recorded |
| Engineering/platform | Go boundaries, AWS profile, API contract, reliability | Not recorded |
| GitHub platform | App installation, permissions, webhooks, PR publication | Not recorded |
| Data/ADR platform owner | Source of truth, PostgreSQL/vector/embedding pipeline, freshness | Not recorded |
| Security | Threat model, tenancy, IAM, egress, secret handling, supply chain | Not recorded |
| Privacy/legal | Model processing, retention, residency, user notice | Not recorded |
| SRE/operations | SLO, on-call, alerts, DR, runbooks, recovery | Not recorded |
| QA/evaluation owner | Labels, metrics, quality gates, release evidence | Not recorded |
| Finance | Cost model, quotas, allocation | Not recorded |

## Appendix A: relationship to current prototype

The current GitHub Actions Pathfinder prototype is a proving ground for user submission, normalization, generic typed evaluation, evidence references, result reporting, and repeatable workflow stages. It is not the AWS service described by this target PRD. Its checked-in catalog and evaluation corpus must not be presented as the authoritative company ADR source or as independently validated model accuracy. GitHub Actions can remain a development/demo backbone; the final product moves durable async execution to the approved AWS workflow architecture if that remains the accepted decision.

## Appendix B: source documents used

- `docs/PROJECT_BRIEF.md`
- `docs/architecture-overview.md`
- `docs/AI_PIPELINE.md`
- `docs/RPC_AND_PROTOBUF.md`
- `docs/DATA_MODEL.md`
- `docs/OPERATIONS.md`
- `docs/PRE_IMPLEMENTATION_READINESS.md`
- `docs/MVP_DECISION_PACKET.md`
- `docs/REQUIREMENT_TO_PROOF_MATRIX.md`
- `docs/OPEN_QUESTIONS.md`
- `docs/SECURITY.md`
- `docs/EVALUATION.md`
- `docs/contracts/API_CONTRACT.md`
- `docs/contracts/EVIDENCE.md`
- `docs/contracts/LOGGING_AND_AUDIT.md`
- `docs/DECISIONS.md`

## Appendix C: AWS API references

- [API Gateway HTTP API IAM authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html) — HTTP API routes can require SigV4 and `execute-api` permission; resource policies are not supported for HTTP APIs.
- [API Gateway invocation IAM policies](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html) — route-specific IAM resource formats and invocation permissions.
- [AWS Signature Version 4](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html) — request signing, temporary credentials, and SDK/CLI guidance.
- [API Gateway REST API IAM authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/permissions.html) — REST API IAM authorization and policy options relevant to private endpoint alternatives.
- [CloudWatch OpenTelemetry setup](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPGettingStarted.html) — AWS documents OTLP ingestion options for logs, metrics, and traces, including Collector/ADOT paths; the PRD treats CloudWatch as a target assumption, not a selected deployment.

