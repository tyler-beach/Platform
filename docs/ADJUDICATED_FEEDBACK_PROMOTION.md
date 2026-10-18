# Adjudicated feedback export

This stage is a controlled bridge from review events to evaluation work. It intentionally exports **candidates**, not automatic additions to `.poc/evaluation/cases.jsonl`.

## Eligibility gates

An event must be `review.adjudicated`, carry `adjudication_status=adjudicated`, `promotion_status=approved`, a known evaluation label, and a controlled feedback route. Only `candidate_train` and `candidate_validation` are exportable. Holdout and evaluation splits are excluded from tuning candidates.

The export preserves the source event ID/hash, unit ID, analysis run/version, adjudicator, evidence references, label, rationale, and split. It emits a deterministic candidate ID and an export fingerprint. The baseline corpus is never modified.

## Run

```sh
python -m unittest discover -s .poc/tests -p 'test_promote_review_feedback.py' -v
python .poc/review_sampling/promote_review_feedback.py --ledger /path/to/review-events.jsonl --output /tmp/evaluation-candidates.json
```

The event must pass the hash-chain and schema validation in `review_events.py`. The export is a queue for a separate corpus review step. A human must convert the candidate into a complete, reproducible scenario with pinned source artifacts, expected disposition and counter-evidence; reviewers must check for duplicate/leakage and keep holdout cases untouched. Then run the existing offline labeled evaluation and compare versioned slice metrics before any reviewed release.

This prototype does not authenticate adjudicators, validate evidence IDs against an evidence store, generate runnable test fixtures, write to the corpus, or update model/rules. The JSONL ledger and export are local demo artifacts, not production services.
