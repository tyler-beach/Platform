# Offline human review sampling prototype

This is a deterministic, standard-library-only prototype for generating a review batch from a JSONL frame. It is not a deployed queue, reviewer assignment system, transactional store, or production quality estimate.

## Input frame

Each JSONL row is one deduplicated requirement × analyzed artifact snapshot × analysis run unit:

```json
{"unit_id":"repo-a:ADR-12:commit-abc:run-42","outcome":"inconclusive","evidence_band":"low","impact":"high","risk_flags":["UNRESOLVED_SOURCE"]}
```

Required fields: `unit_id`, `outcome` (`deviation`, `no_deviation`, `potential`, `inconclusive`), and `evidence_band`. Optional: `impact` and `risk_flags`. Duplicate unit IDs and unknown outcomes are rejected.

## Run

```sh
python .poc/review_sampling/sample.py --input frame.jsonl --output review-batch.json --seed pilot-2026-01 --per-stratum 2
python -m unittest .poc.tests.test_review_sampling -v
```

The batch manifest includes a canonical frame fingerprint, per-stratum population/selected counts, inclusion probabilities, inverse-probability design weights, and the actual selected unit IDs. A seed is useful for reproducibility, but the stored manifest remains the record of what was selected.

The probability sample is stratified by outcome × evidence band. The risk queue separately includes explicit risk flags and high/critical impact. Risk items have no population inclusion probability and must not be pooled into weighted quality estimates. If a unit appears in both queues, it is one operational unit with two selection reasons; the queues remain separate for estimation.

This first prototype deliberately stops before reviewer assignment and feedback persistence. Before connecting it to real data, define tenant-scoped authorization, immutable snapshot IDs, retention, access controls, transactional append-only review events, nonresponse accounting, and a reviewed sampling policy. The current evidence-strength score is not a correctness probability.
