# ADR-PLATFORM-001 — Preserve service availability during voluntary disruption

- **Status:** Accepted (prototype corpus)
- **Decision owner:** Platform Architecture
- **Scope:** Production Kubernetes workloads where availability during voluntary disruption is required.

## Decision

Workloads classified as availability-sensitive **MUST declare and maintain a disruption budget**.
Tier-1 services MUST keep at least two pods available (`minAvailable: 2` or equivalent).

## Notes

Prototype stand-in for org policy. Replace when importing real ADRs.
