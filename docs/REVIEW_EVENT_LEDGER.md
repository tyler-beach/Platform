# Append-only review event ledger (offline prototype)

The sampler produces candidates; this ledger records human decisions without mutating the original analysis result. A reviewer disposition is not automatically an adjudicated evaluation label.

## Event contract

Each `review.dispositioned` or `review.adjudicated` event records:
- stable event and review-unit IDs;
- the immutable analysis run and analysis/pipeline version;
- actor ID and timezone-qualified timestamp;
- a controlled disposition and reason code;
- evidence IDs (references only) and a concise rationale;
- optional `supersedes_event_id` for corrections, never in-place edits;
- a previous-event hash and event hash for tamper-evident ordering.

The ledger rejects duplicate event IDs, invalid disposition/reason values, missing version references, timezone-free timestamps, duplicate evidence references, and supersedes references to absent events. It refuses raw prompts and source excerpts. It does not prove the actor's identity or authorization; those are deployment-layer responsibilities.

## Run locally

```sh
python -m unittest discover -s .poc/tests -p 'test_review_events.py' -v
```

The implementation uses an append-only JSONL file and an advisory file lock for a local single-host demo. Hash chaining detects accidental or deliberate edits to existing records, but does not provide signatures, trusted timestamps, remote anchoring, or protection against an attacker who can rewrite the whole file and recompute the chain. It is not a multi-tenant production event store.

Before promotion to a production API, add authenticated actor identity, authorization and tenant boundaries, durable transactional persistence, retention controls, key management/signatures or external checkpoints, concurrent-writer tests, and an adjudication workflow. Keep event ingestion separate from evaluation-corpus promotion; only adjudicated and versioned labels should enter the evaluation baseline.
