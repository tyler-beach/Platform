# Issue → package → catalog evaluation

Submit a **pinned evidence package** through a GitHub Issue and receive a catalog evaluation comment. This is the inbound path for the synthetic multi-ADR catalog (`ADR-101`–`ADR-200`).

## Safety (public repository)

- Use only **synthetic** or explicitly **public** content.
- Do not paste secrets, credentials, private customer data, or proprietary source.
- The result comment includes hashes, outcomes, and counts — **not** full tech-spec/code bodies.
- The full report JSON is a workflow artifact (`pathfinder-issue-evaluation-*`).

## How to submit

1. Open **New issue** → **Pathfinder analyze package**.
2. Check the public/synthetic attestation box.
3. Preferred: paste a complete `pathfinder-evidence-package-v1` object in **Full package JSON** (optionally inside a ` ```pathfinder-package ` fence).
4. Or fill **Tech spec**, **Sample code**, **Observations JSON array**, and optional **Domains**.
5. Submit. The **Pathfinder Issue Package Evaluation** workflow runs on open/edit/label and comments results.

You can also re-run via **Actions → Pathfinder Issue Package Evaluation → Run workflow** with an issue number.

## Package shape

Minimum:

```json
{
  "schema_version": "pathfinder-evidence-package-v1",
  "package_id": "my-service",
  "scope": { "domains": ["identity", "security"] },
  "observations": [
    {
      "evidence_id": "EV-1",
      "predicate": "session.ttl_seconds",
      "subject": "session",
      "value": 720,
      "artifact_id": "tech_spec",
      "revision": "sha256:…",
      "path": "issue/tech-spec.md",
      "source_sha256": "…",
      "locator": { "kind": "tech_spec_claim", "value": "session.ttl_seconds" }
    }
  ]
}
```

Intake recomputes `sha256` / `revision` from any pasted `tech_spec` / `code` content so digests stay pinned to the body text.

Observations are **required**. Free-form prose alone is not auto-parsed into predicates; missing evidence stays `inconclusive`.

Predicates must be registered and collectable via `structured_package` (see `.poc/requirement_catalog/predicates.json`).

## Local dry-run

```sh
python3 .poc/issue_analyze/issue_package.py \
  --issue-number 0 \
  --body-file .poc/issue_analyze/fixtures/sample_issue_body.md \
  --work-dir /tmp/pathfinder-issue \
  --run-url https://example.invalid/run
```

## Related

- Catalog evaluation CLI: `docs/REUSABLE_REQUIREMENT_EVALUATION.md`
- Sample package: `.poc/requirement_catalog/sample_packages/multi-domain-session-service/`
- OpenSpec change: `openspec/changes/issue-package-evaluation/`
