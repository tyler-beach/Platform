# Adversarial grill: github-input-adapters

**Method:** ADVERSARIAL_DESIGN_REVIEW + FUNCTIONAL_CORE (no grillme skill).  
**Depends on:** github-actions-go-pathfinder.

## Findings

| ID | Severity | Failure mode | Resolution |
|----|----------|--------------|------------|
| I1 | P0 | SSRF / arbitrary host fetch via crafted URL | Only GitHub API/`gh` for `github.com` PR refs; reject other hosts |
| I2 | P0 | Fork PR exfiltrates or analyzes untrusted code as trusted | Same-repo default; allowlist + attestation for exceptions |
| I3 | P1 | Token with contents:read over-fetches secrets in repo | Skip likely-secret paths (`.env`, `*.pem`) + size caps; never log bodies |
| I4 | P1 | Partial file fetch presented as full coverage | Limitations array required when files skipped |
| I5 | P2 | Path traversal in bundle paths (`../`) | Normalize and reject `..` / absolute paths |

## Deferred

- Private submodule recursion
- Cross-org ADR packs
