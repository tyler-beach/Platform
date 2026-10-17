# Synthetic natural-language ADR corpus

This corpus contains 50 distinct Markdown ADRs under `adrs/`, with one small source fixture per case under `fixtures/`. ADR files use ordinary decision prose and do not contain machine-only rule syntax. `manifest.jsonl` holds the synthetic gold disposition, evidence capability, exact requirement passage, pinned artifact hashes, and expected source fact (when available).

The cases span availability, authentication, authorization, encryption, data management, network security, observability, and resilience/operations. Thirty-five cases have a declared YAML configuration fact for the structured collector. Fifteen intentionally require unavailable runtime-state evidence and use unsupported Terraform-shaped placeholders; they must remain inconclusive.

Run `python .poc/evaluation/evaluate_adr_corpus.py --output-dir /tmp/adr-corpus-audit` from the repository root. The audit checks corpus integrity and deterministic evidence collection only. Gold labels are synthetic and unadjudicated; no model is invoked, and the audit does not measure semantic quality or calibrate confidence.
