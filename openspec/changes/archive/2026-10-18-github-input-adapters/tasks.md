## 1. Specs

- [x] 1.1 Proposal, design, specs
- [x] 1.2 Grill (`GRILL.md` / `DECISIONS.md`); `openspec validate github-input-adapters --strict`

## 2. Implementation

- [x] 2.1 TDD: PR URL parser + same-repo allow rules
- [x] 2.2 TDD: PR fetch fake client with caps/denylist/fork denial
- [x] 2.3 TDD: multi-file via PR only (issue form field; no zip bundles)
- [x] 2.4 Wire intake stage + issue form field + `gh` client
- [x] 2.5 Behavioral fixture: fake PR payload → package (intake test)
- [x] 2.6 Docs update

## 3. Verification

- [x] 3.1 Go tests green
- [x] 3.2 Workflow CI green / PR merge
