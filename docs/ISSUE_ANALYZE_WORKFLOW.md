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
3. Paste your **Tech spec (markdown)** and/or **Sample code** (Go, Python, or JSON). Domains optional.
4. Leave **Observations JSON** empty unless you want to override extraction.
5. Submit. The workflow extracts allowlisted predicates, evaluates the catalog, and comments results.

You can still paste a complete `pathfinder-evidence-package-v1` in **Full package JSON** if you prefer.

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

## Local dry-run

```sh
# Paste-only issue body (no observations JSON)
python3 .poc/issue_analyze/issue_package.py \
  --issue-number 0 \
  --body-file .poc/issue_analyze/fixtures/paste_only_issue_body.md \
  --work-dir /tmp/pathfinder-issue \
  --run-url https://example.invalid/run

# Or evaluate a package with tech_spec/code and empty observations
python3 .poc/requirement_engine/evaluate_package.py /path/to/package.json
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
