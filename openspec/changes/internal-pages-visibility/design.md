# Design: bind real-data export to an organization and private Pages audience

Extend the pure visibility check with `repository_owner_type`. Require an exact organization owner and repository visibility in `{private, internal}` when opt-in is true. Keep the `pages_public is False` identity check and exact string opt-in. With opt-in false or absent, return false without attempting ledger access, preserving fixture-only builds.

The docs workflow passes `.owner.type` from the repository API response. Tests cover both accepted organization visibility values plus public, user-owned, public Pages, unknown Pages, and disabled opt-in cases.
