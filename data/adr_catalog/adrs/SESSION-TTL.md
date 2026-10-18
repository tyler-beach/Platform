# ADR-PLATFORM-002 — Limit session lifetime to 60 minutes

- **Status:** Proposed
- **Decision owner:** Identity and Platform Architecture
- **Scope:** Authenticated user and service sessions managed by platform-owned authentication components.
- **Effective date:** Upon approval
- **Review trigger:** A change to session-risk classification, identity-provider capabilities, or approved authentication policy.

## Context

Long-lived sessions increase the period during which a stolen or unattended session credential can be reused. Session lifetime is a security property of the system's behavior; it should not depend on a particular programming language, framework, token format, or storage implementation.

## Decision

The maximum permitted lifetime of an authenticated session **MUST be 60 minutes**.

The session lifetime is measured from the time the session is established. At or before the 60-minute boundary, the system MUST reject the expired session for authenticated access and require a new authentication event or an explicitly approved reauthentication flow.

Implementations MUST NOT extend the lifetime of the existing session beyond the 60-minute maximum merely because the session is active or a request is received. If a renewal mechanism is supported, renewal MUST preserve the maximum lifetime rule by creating a newly authenticated session under the approved policy; it MUST NOT silently turn the limit into an unlimited sliding expiration.

The policy applies regardless of whether the session is represented by a cookie, bearer token, server-side session record, or another mechanism.

## Rationale

A language-neutral behavioral requirement allows architecture review to evaluate observable security semantics across heterogeneous systems. It avoids treating one configuration field or one framework's default as sufficient evidence.

## Consequences

- Session creation time and expiration semantics must be identifiable from configuration, code, or runtime evidence.
- Absolute and idle timeout settings must be distinguished. An idle timeout shorter than 60 minutes may be stricter, but an idle timeout alone does not demonstrate a 60-minute absolute maximum if activity can extend the session indefinitely.
- Token expiration, server-side session expiration, refresh behavior, and revocation paths may need to be assessed together.
- Systems that cannot establish the effective expiration boundary must be reported as inconclusive.

## Conformance evidence

Evidence may include approved identity policy, effective session configuration, token or session lifetime claims, refresh/renewal behavior, and tests or runtime observations demonstrating rejection at expiration. Evidence must be tied to the assessed version and environment.

A configured value of 60 minutes is not by itself sufficient if another component can renew or accept the session beyond the limit.

## Validation examples

- **Potential deviation:** A session's absolute lifetime is configured to 90 minutes.
- **Potential deviation:** An active session receives rolling extensions and can remain valid beyond 60 minutes without a new authentication event.
- **Aligned:** The session is rejected at the 60-minute boundary, and any renewal requires a new authentication event under the approved policy.
- **Inconclusive:** A token advertises a 60-minute expiration, but the system's acceptance or refresh behavior is not available for inspection.

These examples illustrate the policy and are not claims about a live system.
