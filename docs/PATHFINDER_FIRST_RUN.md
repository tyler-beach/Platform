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
