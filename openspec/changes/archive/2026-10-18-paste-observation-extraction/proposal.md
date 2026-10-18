## Why

Issue intake still requires hand-authored observation JSON. Users want to paste a real tech-spec and/or Go/Python sample and get catalog results. Without a fail-closed extractor, free text stays unevaluated (`inconclusive`) or intake rejects the submission.

## What Changes

- Add a deterministic paste extractor that turns pinned tech-spec/code artifacts into typed observations for an allowlisted set of catalog predicates.
- Fail closed: emit only high-confidence grounded values; never invent negatives from silence; drop conflicting values for the same predicate+subject.
- Wire extraction into issue intake and package evaluation when observations are omitted but tech_spec/code content is present.
- Update the issue form and docs so observations are optional when paste content is provided.
- Keep result comments free of full source bodies.

## Capabilities

### New Capabilities
- `paste-observation-extraction`: Deterministic extraction of typed catalog observations from pasted markdown/Go/Python evidence.

### Modified Capabilities
- `issue-package-evaluation`: Observations JSON becomes optional when tech_spec and/or code content is present; intake runs extraction before evaluate.

## Impact

- `.poc/requirement_engine/paste_extractor.py` (+ language helpers)
- `.poc/issue_analyze/issue_package.py`, issue template, `docs/ISSUE_ANALYZE_WORKFLOW.md`
- Tests with messy real-looking fixtures (not sterile predicate checklists)
- Unextracted predicates remain `inconclusive` by design
