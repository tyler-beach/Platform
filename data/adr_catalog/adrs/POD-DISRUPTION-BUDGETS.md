# ADR-PLATFORM-001 — Preserve service availability during voluntary disruption

- **Status:** Proposed
- **Decision owner:** Platform Architecture
- **Scope:** Production workloads orchestrated by Kubernetes where availability during planned or voluntary disruption is a service requirement.
- **Effective date:** Upon approval
- **Review trigger:** A material change to service availability objectives, workload topology, or disruption-management policy.

## Context

Node maintenance, cluster upgrades, autoscaling, and other voluntary disruptions can remove workload replicas at the same time. If too many replicas are disrupted concurrently, a service may become unavailable even when its application instances are healthy. The control must express the availability intent independently of a programming language, deployment tool, or specific workload manifest.

## Decision

Workloads classified as availability-sensitive **MUST declare and maintain a disruption budget** appropriate to their service availability objective.

The budget MUST constrain voluntary disruptions so that the workload retains the minimum availability agreed for that service. The policy MUST be expressed using a workload-appropriate minimum-available or maximum-unavailable constraint, with a value derived from the service's replica topology and availability objective.

A workload MUST NOT be considered compliant solely because a disruption-budget resource exists. Assessment MUST establish that:
- the budget selects the intended workload;
- the budget's availability constraint is defined and valid for the workload;
- the constraint is consistent with the service's declared availability objective and replica topology; and
- the relevant workload and budget are both in the assessed environment and version.

Where the workload's desired availability, replica count, selector relationship, or effective budget cannot be established from available evidence, the result MUST be **inconclusive**, not compliant.

## Rationale

This decision defines an observable availability invariant rather than prescribing a particular manifest, programming language, or deployment implementation. It permits different workload shapes while requiring the same outcome: planned disruption must respect the workload's availability requirement.

## Consequences

- Workload specifications and deployed configuration need to expose the availability objective, workload identity, and effective disruption budget.
- Static configuration checks can verify resource presence, selectors, and configured values, but runtime or cluster evidence may be required to establish effective behavior.
- A budget that exists but selects no intended pods, conflicts with the service objective, or cannot be evaluated is not proof of compliance.
- Workloads that cannot tolerate voluntary disruption need an explicit, reviewed policy rather than an assumed default.

## Conformance evidence

Acceptable evidence may include version-pinned workload and disruption-budget definitions, resolved selector relationships, declared availability objectives, replica configuration, and—where required—cluster observations showing the effective resources.

Each finding MUST identify the exact source version and relevant field or line range. Missing, stale, contradictory, or out-of-scope evidence MUST be recorded as a coverage gap.

## Validation examples

- **Potential deviation:** An availability-sensitive workload declares three replicas and requires at least two available, but its effective budget permits two replicas to be voluntarily unavailable.
- **Aligned:** The effective budget selects the intended workload and constrains voluntary disruption consistently with the approved availability objective.
- **Inconclusive:** A budget exists, but the evidence does not establish whether its selector matches the workload or whether the declared replica topology is current.

These examples illustrate the policy and are not claims about any live cluster.
