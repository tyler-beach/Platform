# Grill-me decisions for M2 (input adapters)

Depends on M1 (`github-actions-go-pathfinder`).

| ID | Decision |
|----|----------|
| Q14/Q20 | Multi-file intake = **same-repo PR changed files only**; issue form stays tech-spec + single sample code (no issue zip/bundles). |
| Q16 | Ship after M1; Q10 success only after M2. |
| Q19 | Forks rejected. |
| Q21 | Fetch **changed files** in the PR (text, within caps), not entire tree. |
| Q22 | Tech-spec section **optional** when PR adapter used. |
| Q27 | Denylist skip (`.env*`, `*.pem`, keys, etc.) + limitations; do not fail whole job solely for denylist hits. |
| Q28 | Caps: 50k chars/field, 200k package JSON; PR pack ≤ ~1 MiB text / ≤ 50 files. |
