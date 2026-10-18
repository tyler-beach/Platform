# ADR-PLATFORM-002 — Limit session lifetime to 60 minutes

- **Status:** Accepted (prototype corpus)
- **Decision owner:** Identity and Platform Architecture
- **Scope:** Authenticated user and service sessions.

## Decision

The maximum permitted lifetime of an authenticated session **MUST be 60 minutes**.
Idle timeout alone does not satisfy this absolute maximum.

## Notes

Prototype stand-in. Aligns with language-neutral SESSION-TTL policy used in demos.
