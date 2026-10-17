# Design: language-neutral evidence for ADR assessment

## Goals

Keep the domain model independent of programming language and source format. Extract deterministic, versioned facts at source boundaries, then compare those facts with applicable ADR requirements. Preserve exact provenance and uncertainty through every transformation.

## Pipeline boundaries

1. **Resolve decisions and applicability.** Select current decision versions and determine repository, service, environment, resource, ownership, and time scope. A language filter is used only when the ADR explicitly makes language relevant.
2. **Plan evidence capabilities.** Derive the evidence needed for each requirement from its declared/assessed concepts and the analysis mode. Select available source adapters (for example, language frontends, IaC/config parsers, or runtime snapshot readers). Record required and optional capabilities before collection.
3. **Collect source facts.** Adapters parse and resolve their supported source. They emit observations and a collection report describing scanned versions, files/resources, unsupported constructs, exclusions, diagnostics, and coverage.
4. **Normalize observations.** Convert source-specific facts into a small shared envelope without discarding original locators or source details. Use typed values where possible; retain source-specific payloads only as versioned, bounded details.
5. **Build a derived behavior view.** Summaries such as “request handling can synchronously reach an external provider” may combine observations. Each claim identifies its supporting and contradicting observation IDs, source references, resolution basis, and derivation version. A prose summary alone is never evidence.
6. **Assess requirements.** Run deterministic evaluators for crisp, supported predicates. Use bounded semantic assessment for natural-language interpretation or relationships that cannot be decided deterministically. The assessor receives only applicable requirements and their linked evidence package.
7. **Validate and classify.** Application code checks requirement version, applicability, evidence IDs, artifact versions, locators, observation derivations, and coverage. Return aligned, deviation, or inconclusive per requirement. Missing evidence stays explicit.

## Observation envelope

The initial contract should remain deliberately small and source-neutral:

- `observation_id`: stable within the analysis run and derived from canonical inputs;
- `subject`: logical resource, component, symbol, or configuration object when resolvable;
- `predicate`: a versioned, namespaced observation kind (not a requirement-specific rule name);
- `value`: bounded typed value or structured relation;
- `source_ref`: immutable artifact/version/hash plus exact source-specific locator (path and lines, JSON pointer, resource address, API object/version, or equivalent);
- `collector`: adapter name/version and parsing/analysis method;
- `resolution`: direct, statically resolved, approximate, or unresolved, with explanation;
- `evidence_class`: declared configuration, static code observation, specification statement, or runtime observation;
- `derivation_refs`: observation IDs used to derive this fact, when applicable.

Observation kinds should be added only when they serve more than one requirement or enable a clearly reusable capability. This change does not define a universal vocabulary for every architectural domain.

## Coverage and negative evidence

Each adapter returns a collection report alongside observations. The report binds to the exact source snapshot and states what it inspected, what it could not inspect, and which required capabilities it satisfied. Absence is meaningful only if the relevant scope was enumerated and collection coverage is sufficient for that claim. An unsupported file, dynamic code path, unresolved template, inaccessible runtime, or failed branch produces incomplete evidence—not a negative observation.

Requirement evaluation must distinguish:

- **Aligned:** applicable requirement has sufficient supporting observations and no unresolved material contradiction.
- **Deviation:** applicable requirement has validated observations that contradict it.
- **Inconclusive:** applicability, interpretation, coverage, resolution, or evidence is insufficient or mixed.

No applicable ADR is a retrieval/applicability outcome, not a compliance result.

## Reusable adapters and requirements

Adapters are organized by source/evidence capability, not ADR ID. A programming-language frontend may use AST, compiler, symbol, or data-flow analysis internally, then emit shared observations. An infrastructure adapter may parse Terraform or rendered deployment configuration. A runtime adapter may read a pinned, authorized snapshot. These adapters do not decide whether a particular ADR is satisfied.

For example, a token-lifetime requirement and a storage-encryption requirement may both consume configuration observations from an IaC adapter. Their predicates and applicability differ, but neither requires an ADR-specific parser. A PDB requirement may consume Kubernetes resource observations and, when the claim concerns current cluster state, a distinct runtime observation.

The ADR remains authoritative natural-language source. Requirement extraction is derived and versioned. It may propose atomic obligations, scope, exceptions, and evidence needs, but ambiguous or unsupported interpretation remains for review. Do not silently turn every new ADR into a machine-enforced predicate.

## Language-specific analysis boundary

ASTs and language tooling are implementation details of source adapters. They can establish syntax, definitions, call edges, selected data/config flows, and uncertainty. They cannot establish intent or policy compliance merely from names or syntax. A language frontend may emit a language-neutral observation only when its meaning is justified by resolved source facts; otherwise it emits a lower-confidence/unresolved observation or diagnostic.

Do not make language part of the canonical ADR-to-code matching contract. Keep source language as provenance and as an optional applicability attribute. Do not require identical AST features across languages; require compatible observations and explicit limitations instead.

## Verification and test design

- Unit/table tests for observation validation, canonical IDs/order, provenance matching, capability planning, coverage gates, and outcome classification.
- Adapter contract tests proving source locators and artifact versions survive normalization.
- Cross-language fixtures expressing the same behavior and producing equivalent observation shapes, while preserving adapter-specific resolution details.
- Cross-source fixtures for one requirement backed by code and configuration; verify that disagreement or missing coverage produces inconclusive.
- Negative-evidence tests proving that partial scans, unsupported constructs, missing runtime access, and unresolved templates cannot produce aligned or confirmed absence.
- Labeled evaluation for requirement interpretation and semantic summaries; track evidence-link validity and abstention separately from prose similarity.

## Risks and open design questions

- A canonical predicate vocabulary can become a premature ontology. Keep initial kinds few, namespaced, versioned, and evidence-driven.
- Natural-language requirements may be ambiguous or combine several obligations. Preserve source passages and reviewer disposition; do not infer a deterministic rule where none is approved.
- Cross-source identity resolution (repository component to cloud resource to runtime object) may be incomplete. Treat joins as versioned claims with provenance and uncertainty.
- Static analysis cannot prove runtime behavior or enumerate every dynamic path. Collection coverage and resolution status must constrain conclusions.
- Open decisions before implementation: minimum initial observation kinds; how to represent capability requirements; locator schema; equivalence rules for cross-language fixtures; and which source adapter is the first vertical slice.
