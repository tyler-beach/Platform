## Context

Shared spine exists for two wired families. Users need breadth: one package → many requirement results.

## Goals / Non-Goals

**Goals**
- 100 synthetic ADRs with typed approved requirements
- Predicates/collectors grow by domain; ADRs are data
- Evaluate a package to a multi-result report with aggregate status
- Map “partially aligned” to aggregate language: some requirements aligned, some not / inconclusive—not a new engine outcome inventing partial compliance

**Non-Goals**
- Perfect NL ADR parsing for arbitrary prose
- Live cloud/cluster collectors
- Independent human adjudication of the 100 ADRs
- Claiming production accuracy

## Decisions

1. Generate catalog via checked-in generator + committed artifacts for deterministic CI.
2. Structured evidence package is the primary input (tech_spec + code + optional direct observations).
3. Engine outcomes stay: supported_deviation | no_deviation_found | not_applicable | inconclusive. Aggregate adds `mixed` / `insufficient_coverage`.
4. New kinds only for reusable families: `numeric_min`, `dependency_forbidden`.

## Risks

- Synthetic labels are not adjudicated truth.
- Pattern collectors are shallow; missing evidence must stay inconclusive.
