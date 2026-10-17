## Workflow and audit persistence

- [x] 1.1 Add RED-first CLI/CSV integration tests for configuration-only runs, missing-language rejection for code, event stage records, and observation/coverage rows.
- [x] 1.2 Add additive CSV schemas for observations and collection reports; prove existing table headers stay byte-for-byte compatible.
- [x] 1.3 Sanitize collector diagnostics before they are persisted or printed; add canary-secret tests across all outputs.
- [x] 1.4 Update the GitHub Actions input contract to support `none` and pass `config_source`; skip language toolchain setup for configuration-only analysis.
- [x] 1.5 Add end-to-end test proving a config-only run persists evidence, confidence components, findings, collection coverage and event records.

## Corpus and evaluation

- [x] 2.1 Create 50 natural-language synthetic ADRs across the agreed architecture domains and a separate JSONL gold manifest.
- [x] 2.2 Add an offline corpus audit for ADR count/uniqueness, hashes, locators, supported facts and expected inconclusive cases.
- [x] 2.3 Add behavioral tests for all manifest cases and report extraction/evidence-mapping metrics separately from mock semantic abstention.
- [x] 2.4 Run the corpus audit from the existing GitHub Actions evaluation workflow and upload Markdown/JSON reports.

## Verification and review

- [x] 3.1 Run focused tests RED then GREEN and the full PoC unit suite.
- [x] 3.2 Validate OpenSpec strictly and validate workflow YAML syntax/inputs.
- [x] 3.3 Run config-only and code-based end-to-end PoC paths; inspect CSV joins and report/source provenance.
- [x] 3.4 Record corpus labels as synthetic and unadjudicated; do not tune/claim live model quality or calibrated confidence from mock results.
- [ ] 3.5 Review security/privacy impact, remaining risks and deployment state; do not archive until acceptance and current-state docs are reconciled.
