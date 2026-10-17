# Design

## Experience

The demo gains a focused investigation workspace above the generated scenario gallery. Two tabs select the policy example. A vertical evidence chain makes the relationship between required behavior, an observed condition, and a candidate finding visible. Evidence rows are selectable; a persistent side rail provides the analysis trace, a selected-stage explanation, evidence gaps, and local review controls.

The rest of the page continues to use the existing generated gallery and Actions workflow integrations. The new workspace is explicitly synthetic and does not claim to run the repository pipeline or access live infrastructure.

## Decision examples

### Pod disruption budgets

The policy is scoped to availability-sensitive Kubernetes workloads, but is language-neutral. It requires an effective disruption budget aligned with the approved service availability objective and replica topology. Presence of a budget alone is not sufficient; workload selection and effective configuration must be established.

### Session TTL

The policy applies across session representations and technology stacks. The absolute maximum is 60 minutes from establishment. Activity must not extend the same session beyond the boundary; renewal behavior and server-side acceptance need assessment as well as token claims.

## Safety and truthfulness

Example observations are illustrative. The interface labels findings as candidates and review as local-only. It does not present fabricated evidence as a real file excerpt or claim that a synthetic outcome came from a live analysis run. Existing gallery provenance and source text escaping remain unchanged.

## Responsive behavior

At desktop widths, the workspace uses a primary investigation canvas and a secondary analysis rail. Below tablet widths, the rail moves below the canvas; at mobile widths, example tabs and review controls stack. Controls retain visible focus indicators and selected/pressed state.
