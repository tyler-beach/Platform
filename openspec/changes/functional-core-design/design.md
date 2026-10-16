# Design: functional core / imperative shell

## Approach
Make domain computations pure where practical and isolate effects in adapters/use-case orchestration. Inputs to pure functions are complete snapshots/values; outputs are new values or explicit errors. Time, randomness, databases, network, filesystem, workflow APIs and Anthropic remain effects.

## Candidate core functions
- normalize parsed artifact metadata;
- calculate applicability from supplied facts/policy;
- select/canonicalize evidence under a budget;
- validate findings and evidence references;
- classify a state transition;
- compute stable fingerprints;
- map parsed requirements into normalized domain values.

## Effect boundaries
Use-case handlers load authoritative snapshots, call pure transformations, invoke effects through narrow ports, and persist outcomes. Do not make a domain package query repositories, read environment variables, get current time, generate random IDs or call models implicitly.

## Data ownership
Go has no deep immutability. Once a value is passed to another stage, the producer must not mutate it. Copy map/slice containers when ownership transfers; avoid shared mutable pointers; use versioned refs for large text when copying is expensive. Sort evidence IDs, collections and findings before hashing or constructing model input.

## Errors and outcomes
Use idiomatic Go errors with typed categories and wrapping. Inconclusive is a domain outcome; deadline exceeded is an execution failure. Never infer the domain outcome from error strings or zero enum values.

## Distributed effects
Assume delivery can repeat. Use idempotency keys and uniqueness constraints for job creation, persistence and publication. Persist operation identity before side effects where needed. Use an outbox only if reliable event publication warrants it; do not claim exactly-once execution.

## Scope control
This change documents design requirements; it adds no runtime dependency. Do not force abstractions onto code where ordinary Go is clearer.
