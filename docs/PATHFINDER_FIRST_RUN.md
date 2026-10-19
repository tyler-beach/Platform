# Pathfinder first run (collaborators)

Unaided path to a useful catalog evaluation on this repository’s **prototype real ADR pack** (200 org-style ADRs: engineering controls + enterprise standards).

## 1. Open an analyze issue

1. **New issue** → **Pathfinder analyze package**
2. Check the public/synthetic attestation box
3. Leave **Catalog pack** on **Real prototype pack (default)** unless you intentionally want the synthetic ADR-101–200 demo
4. Optionally set **Domains** (e.g. `identity, reliability`). Blank = all pack domains
5. Either:
   - paste a short **Tech spec** (and optional sample code), or
   - link a **same-repo PR** (changed text files), or
   - paste a full `pathfinder-evidence-package-v1` JSON
6. Submit

Pages `/demo` can prepare the issue body (copy / open on GitHub) but does **not** evaluate in the browser.

## 2. Read the comment

Expect:

- Aggregate status (`mixed`, `deviations_found`, `insufficient_coverage`, …)
- Catalog identity (`platform-real-adr-v1`, mode `real`, manifest hash)
- Outcome counts and a short notable-requirements table
- Coverage notes: `inconclusive` = missing extraction, not “ok”
- Each requirement gets one result from all accepted evidence. Evidence provenance retains `design_assertion` for tech specs and `implementation_fact` for code/config; conflicting values are reported as inconclusive with both sources cited
- When semantic extraction is enabled, the comment/report includes extraction status and bounded token usage

## Optional semantic extraction

The default deterministic path is free of provider calls and still useful for explicit patterns. To ask Anthropic to propose additional catalog facts from pasted prose, set repository variable `PATHFINDER_ENABLE_MODEL_EXTRACT=true`, set `PATHFINDER_ANTHROPIC_MODEL` to the approved model ID, and add Actions secret `ANTHROPIC_API_KEY`.

The Go normalizer performs one token-count preflight, stops above 20,000 input tokens, permits at most one generation request with a 4,000-token and 64-fact cap plus a 60-second deadline, and never retries. It validates exact quotes and catalog types before evidence reaches the shared evaluator. Provider failures fall back to deterministic extraction and remain labeled; they do not count as semantic success. This prototype does not run a live Anthropic evaluation in CI.

These are per-invocation limits rather than an organization spend quota. Every issue edit or rerun can invoke the workflow again. Keep semantic extraction off on public repositories; restrict triggers and add a durable quota before enabling it broadly.

Common first-run outcomes:

| Status | Meaning |
|---|---|
| `mixed` | Some aligned, some deviant and/or inconclusive — normal for real pastes |
| `deviations_found` | Confident deviations only |
| `insufficient_coverage` | In-scope rows lack evidence |
| `not_applicable_only` | Domain filter matched nothing |

## 3. Get the full report

Actions → run for your issue → artifact `pathfinder-issue-evaluation-*` (about **14 days** retention) → `report.json`.

Lean index (no source bodies): branch `pathfinder-jobs` → `jobs/jobs.jsonl`.

## 4. Re-run

**Actions → Pathfinder Issue Package Evaluation → Run workflow** with the issue number.

## 5. Swap in your org ADRs later

See `data/adr_catalog/README.md`. Keep this prototype pack until your typed requirements are ready.

## Safety

Public repo: synthetic/public content only. Never paste secrets or proprietary source into issues.
