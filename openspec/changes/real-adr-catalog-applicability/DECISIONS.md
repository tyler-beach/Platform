# Decisions: Real ADR catalog applicability

Frontier decisions for this change. Full interactive grill-me deferred; defaults follow the proposal/design and project guardrails.

| ID | Decision |
|---|---|
| D1 | Keep **synthetic** catalog (ADR-101–200) as the **default** Actions/demo mode until real pack coverage is broader. |
| D2 | Opt-in **real** pack via `PATHFINDER_CATALOG=real` or `--catalog-mode=real` → `data/adr_catalog/`. |
| D3 | First real pack seeds from checked-in `docs/adr` (SESSION-TTL, POD-DISRUPTION-BUDGETS) with typed rows + pack-local copies. |
| D4 | Applicability is a **pure** function: lifecycle active + domain/language metadata filters. No embeddings in this change. |
| D5 | Lifecycle `proposed`/`accepted`/`active` (or empty for synthetic rows) are evaluable; `deprecated`/`superseded`/`rejected` → `not_applicable`. |
| D6 | Empty package domain list does **not** filter (same as today’s synthetic behavior); explicit package domains require intersection. |
| D7 | Reports and issue comments MUST name catalog identity (mode, id, manifest hash). |
| D8 | Findings remain advisory; no merge blocking. |
| D9 | Python `.poc` stays offline oracle; production evaluate remains Go. |
