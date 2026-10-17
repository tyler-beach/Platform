# Proposal: Preserve structured evidence while redacting secrets

## Outcome

Refine source-text redaction so opaque high-entropy credentials are still removed without erasing qualified function names and other structured code identifiers needed to audit analysis evidence.

## Motivation

The current whole-string entropy check redacts some long qualified symbols as if they were credentials. On the Go validation run this erased the provider callee name from `callgraph.json` and caused the remote language check to fail. Losing symbol identity also weakens the evidence a reviewer can inspect.

## Scope

- Detect high-entropy opaque tokens within otherwise structured text.
- Preserve hashes and code identifiers as data, while continuing to remove quoted source literals and known credential forms.
- Add a regression test proving the callgraph retains the exact qualified callee and its source-version reference.

## Non-goals

- Do not disable credential-shaped or source-literal redaction.
- Do not change evidence applicability, confidence scoring, or finding policy.
- Do not claim redaction can identify every secret in arbitrary source.

## Acceptance

- An opaque high-entropy token is redacted even when adjacent to other text.
- Long qualified names such as Go receiver methods remain intact in normalized call-edge observations.
- The CI Go analyzer check passes with an exact provider callee name in the reachable graph.
- Existing credential and literal redaction tests continue to pass.
