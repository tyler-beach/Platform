# ADR-PLATFORM-056 — No sync call in request path to broker

- **Status:** Accepted (prototype corpus)
- **Domain:** messaging
- **Decision owner:** Platform Architecture (prototype)
- **Scope:** Organization-wide standard unless a documented exception exists.

## Decision

Request handlers MUST NOT block on unbounded broker publish retries.

## Notes

Prototype corpus stand-in for org policy. Replace when importing real ADRs.
