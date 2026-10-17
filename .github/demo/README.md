# Functional analysis demo

This directory contains **synthetic test fixtures and a demo-only deterministic harness** for the GitHub Actions workflow `Functional Analysis Demo`.

The Go AST scanner parses the selected synthetic handler with Go's standard-library parser. The Python harness normalizes fixture inputs, builds source-versioned evidence records, estimates a demonstration budget, emits a deterministic mock-model candidate, validates evidence references and writes the report.

The mock-model stage makes no network calls and uses no repository secrets. It is not a real model evaluation and its pass/fail result is only a harness check.
