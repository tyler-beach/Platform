# Design

Add one workflow identity to the existing Actions-history allowlist and one completed-workflow trigger to the docs workflow. The collector continues to call only the Actions workflow-runs and run-jobs endpoints, with its existing run/step caps and field allowlists. It constructs HTML links from the validated repository name and numeric run ID; API-provided HTML URLs are checked against that exact identity.

The documentation workflow's existing `workflow_run` predicate excludes pull-request runs and accepts only runs whose head branch is `main`. Do not download artifacts from the triggering workflow. This keeps code/source evidence out of the history projection and avoids making untrusted workflow artifacts an input to a privileged Pages publisher.

Alternatives considered:
- Download and project the full Functional Analysis Demo artifact: rejected for this iteration because it adds an artifact trust boundary and is unnecessary to show recent executions, stage progression, and outcomes already visible through job/step status.
- Add the workflow as a browser-side GitHub API source: rejected because the static private Pages build already owns the authenticated, bounded collection path.

Security and operations: the collector uses the existing short-deadline API adapter, minimal `actions: read` token scope, bounded response sizes, and no browser token. Existing visibility gates for CSV-backed run records are unchanged. Rollback removes the workflow tuple and trigger entry.
