# ADR-PLATFORM-001 — Preserve service availability during voluntary disruption

- Status: Proposed
- Scope: Availability-sensitive workloads orchestrated by Kubernetes.

## Decision

Availability-sensitive workloads MUST declare and maintain a disruption budget appropriate to their approved service availability objective.

The budget MUST constrain voluntary disruptions consistently with the workload's availability objective and replica topology. Assessment MUST establish that the budget selects the intended workload and that the effective constraint is valid for the assessed environment.

The existence of a disruption-budget resource alone MUST NOT be treated as proof of compliance. If the availability objective, workload relationship, replica topology, or effective budget cannot be established, the result MUST be inconclusive.

This decision defines required behavior; it does not prescribe a programming language, manifest layout, or deployment tool.
