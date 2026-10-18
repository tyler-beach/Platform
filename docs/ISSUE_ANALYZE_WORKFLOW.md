# Issue → package → catalog evaluation

Submit a **pinned evidence package** through a GitHub Issue and receive a catalog evaluation comment. This is the inbound path for the synthetic multi-ADR catalog (`ADR-101`–`ADR-200`).

## Safety (public repository)

- Use only **synthetic** or explicitly **public** content.
- Do not paste secrets, credentials, private customer data, or proprietary source.
- The result comment includes hashes, outcomes, and counts — **not** full tech-spec/code bodies.
- The full report JSON is a workflow artifact (`pathfinder-issue-evaluation-*`).

## How to submit (paste a real sample)

1. Open **New issue** → **Pathfinder analyze package**.
2. Check the public/synthetic attestation box.
3. Either:
   - Link a **same-repo pull request** (changed text files are fetched at the PR head; forks denied), and/or
   - Paste **Tech spec (markdown)** and/or a single **Sample code** snippet. Domains optional.
4. Leave **Observations JSON** empty unless you want to override extraction.
5. Submit. The workflow extracts allowlisted predicates, evaluates the catalog, and comments results.

Tech spec is optional when a same-repo PR is provided. Multi-file code must come from the PR adapter (not zip/bundles). You can still paste a complete `pathfinder-evidence-package-v1` in **Full package JSON** if you prefer.

Re-run via **Actions → Pathfinder Issue Package Evaluation → Run workflow** with an issue number.

## What extraction can and cannot do

The paste extractor (`paste_heuristic_v1`) is deterministic (no model calls). It emits observations only for high-confidence matches, for example:

- Session TTL / idle timeout with explicit units
- Encryption at rest, TLS policy tokens (`tls-1-2-strict`, `tls-1-3-only`, `legacy-ssl`)
- Replicas, probes, retries, DLQ claims
- Rate limit / auth middleware signals in prose or Go/Python
- Hardcoded secret-like literals → `security.secret_in_source.present=true` only
- Sensitive log phrases → `privacy.sensitive_log.present=true` only

It does **not**:

- Treat “not mentioned” as `false` for most presence checks
- Cover all 100 catalog predicates from arbitrary prose
- Invent values when two conflicting numbers appear (both dropped)

Unmatched requirements stay `inconclusive`. Aggregate status is often `mixed` for real pastes.

## Runtime

Production evaluate runs on **GitHub Actions** via the Go Pathfinder runtime (`go/pathfinder`), orchestrated as staged reusable workflow jobs (intake → ensure observations → evaluate → publish → job ledger). AWS is not required. Python under `.poc/` remains an offline oracle, not the production entrypoint.

Lean job index lines append to the `pathfinder-jobs` branch (`jobs/jobs.jsonl`). Full reports stay in workflow artifacts. Findings are advisory (`synthetic_unadjudicated`); they do not block merges. Same-repo PR file intake is a follow-on milestone.

## Local dry-run

```sh
cd go/pathfinder
go build -o /tmp/pathfinder-issue-analyze ./cmd/pathfinder-issue-analyze
go build -o /tmp/pathfinder-evaluate-package ./cmd/pathfinder-evaluate-package

# Paste-only issue body (no observations JSON)
/tmp/pathfinder-issue-analyze \
  --issue-number 0 \
  --body-file ../../.poc/issue_analyze/fixtures/paste_only_issue_body.md \
  --work-dir /tmp/pathfinder-issue \
  --run-url https://example.invalid/run

# Or evaluate a package with tech_spec/code and empty observations
/tmp/pathfinder-evaluate-package ../../.poc/requirement_catalog/sample_packages/multi-domain-session-service/package.json
```

Messy fixtures used in tests:

- `.poc/issue_analyze/fixtures/real_paste_tech_spec.md`
- `.poc/issue_analyze/fixtures/real_paste_session.go`
- `.poc/issue_analyze/fixtures/real_paste_session.py`

## Try it from GitHub Pages

On `/demo` panel **04 / Paste → catalog evaluation**:

1. Check the public/synthetic attestation box.
2. Paste a tech-spec and/or Go/Python/YAML sample (or **Load sample fixture**).
3. **Copy issue body** and/or **Open on GitHub** (short bodies are URL-embedded; large bodies are copied, then the issue form opens).
4. Submit the GitHub issue. Actions extracts observations and comments results.

Pages still only prepares the submission. Live evaluation runs only through GitHub Issues + Actions.

## Related

- Catalog evaluation CLI: `docs/REUSABLE_REQUIREMENT_EVALUATION.md`
- OpenSpec: `openspec/specs/paste-observation-extraction/`, `openspec/changes/pages-paste-eval-bridge/`
