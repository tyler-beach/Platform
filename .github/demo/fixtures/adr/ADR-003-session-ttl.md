# ADR-PLATFORM-002 — Limit session lifetime to 60 minutes

- Status: Proposed
- Scope: Authenticated sessions managed by platform-owned authentication components.

## Decision

The maximum permitted lifetime of an authenticated session MUST be 60 minutes, measured from session establishment.

At or before the 60-minute boundary, the system MUST reject the expired session for authenticated access and require a new authentication event or explicitly approved reauthentication flow. Activity MUST NOT extend the existing session beyond this absolute maximum. Any renewal mechanism MUST preserve this rule rather than silently converting it into unlimited sliding expiration.

The requirement applies regardless of session representation, programming language, framework, or token format. A configured timeout alone is insufficient if another component can accept or renew the session beyond the limit.
