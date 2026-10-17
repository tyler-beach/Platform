# Proposal: Language-neutral evidence for ADR assessment

## Why

ADRs usually state architectural constraints in domain language. They may concern request behavior, authentication policy, cloud resource configuration, deployment topology, resilience, or runtime state. The implementation can span several programming languages and infrastructure formats.

The current executable PoC centers on language-specific call graphs. Those analyzers are useful evidence collectors, but they should not define the platform's domain model or require an ADR to name a programming language. Adding an ADR about token lifetime or storage encryption should not require writing a parser dedicated to that ADR.

## What changes

- Define a source-versioned, language-neutral observation contract for facts extracted from code, infrastructure/configuration, specifications, and runtime snapshots.
- Keep language and format specific parsing in reusable source adapters. Adapters emit observations with precise provenance, resolution quality, and explicit collection coverage.
- Separate ADR applicability from evidence-source selection. Language is an applicability attribute only when the decision itself makes it relevant.
- Assess requirements against observations and source evidence, with deterministic evaluation for crisp predicates and bounded semantic interpretation for natural-language constraints.
- Treat interpretations and summaries as derived, versioned artifacts linked to observations; they are not evidence by themselves.
- Preserve inconclusive outcomes when required evidence is unsupported, incomplete, unresolved, stale, or ambiguous.

## Scope and non-goals

In scope: the observation boundary, reusable adapter responsibilities, requirement-to-evidence matching, provenance/completeness, and acceptance scenarios for heterogeneous source types.

Out of scope: implementing production analyzers or cloud integrations; defining a universal ontology or policy DSL; automatically translating every ADR into enforceable rules; selecting every language/IaC/runtime source to support; changing model provider direction; and enabling automatic enforcement or infrastructure mutation.

## Acceptance criteria

- An accepted ADR requirement can be evaluated against evidence from different implementation languages without changing the ADR or the assessment contract.
- A new requirement over an already supported evidence source does not require an ADR-specific parser or adapter.
- Code, infrastructure configuration, and runtime observations share an envelope with exact versioned provenance while retaining source-specific locators.
- A generated behavior summary cannot support a finding unless it links to validated observations and source evidence.
- Missing adapter support or incomplete source coverage cannot be interpreted as proof of compliance or as proof that a control is absent.
- Requirements and scenarios trace to deterministic tests or measurable acceptance evidence before implementation begins.
