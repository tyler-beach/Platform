# OpenSpec current-state specs

These specs describe the initial intended behavior as currently understood. They are the starting behavioral baseline, not proof of implemented code.

For every behavior change:
- create one focused directory directly under openspec/changes/;
- write proposal, delta specs, design when cross-cutting, and testable tasks;
- use ADDED / MODIFIED / REMOVED / RENAMED Requirements in delta specs;
- put at least one Scenario beneath every Requirement;
- review before implementation, verify after implementation, then archive;
- keep these current-state specs aligned with behavior actually shipped.

Capabilities:
- artifact-and-provenance: immutable source versions and evidence chain.
- deviation-analysis: comparison modes, applicability and finding outcomes.
- orchestration-and-reliability: job lifecycle, idempotency and errors.
- secure-ai-execution: bounded model use and untrusted data controls.

Run current CLI validation after OpenSpec initialization. Structural validation does not replace unit, integration, security or AI evaluation.
