const e=`# Logging, tracing, metrics, and audit contract

Logs, distributed traces, product audit history, and AI provenance serve different purposes. They are not interchangeable stores.

## Signal responsibilities

| Signal | Purpose | Authoritative? |
|---|---|---:|
| Application log | Diagnose an operation or failure | No |
| Trace/span | Connect API, workflow, Lambda, DB and provider activity | No |
| Metric | Alert and trend using low-cardinality dimensions | No |
| AuditEvent | Who changed/dispositioned/published what and when | Yes for audited business actions |
| ModelRun | Provenance/evaluation metadata for one model operation | Provenance record, not job state |
| Step Functions execution history | Operational workflow troubleshooting | No, not the only audit record |
| Raw prompt/response | Deep debugging/evaluation only if explicitly retained | No |

Use OpenTelemetry semantic conventions where applicable. Start with standard Go OTel interfaces and an approved exporter; do not bind business policy to a specific tracing vendor.

## Structured log envelope

Every application log should be structured and include available fields:

~~~json
{
  "timestamp": "2026-01-02T03:04:05.006Z",
  "severity": "INFO",
  "service.name": "adr-platform-worker",
  "service.version": "git-sha-or-release",
  "environment": "development",
  "event.name": "analysis.stage.completed",
  "message": "Evidence retrieval stage completed",
  "request.id": "req_opaque",
  "trace_id": "32-hex-otel-trace-id",
  "span_id": "16-hex-otel-span-id",
  "workspace.id": "ws_opaque",
  "job.id": "job_opaque",
  "pipeline.version": "pipeline-version",
  "stage.name": "evidence_retrieval",
  "duration_ms": 143,
  "outcome": "success"
}
~~~

Field names may adapt to a logging library/exporter, but semantics must survive. Use UTC time, stable event names and opaque identifiers.

### Required and conditional fields

- Always: timestamp, severity, service name/version, environment, event name, message, outcome.
- API: request ID, trace/span IDs when available, operation, safe HTTP/gRPC status.
- Job: workspace ID, job ID, pipeline version, stage and attempt when available.
- Model operation: operation, configured/resolved model ID when available, prompt/schema versions and hashes, attempt, latency, token usage, validation result, safe provider request ID and error category.
- Audit: actor identity/service principal, target kind/ID/version, action, outcome, timestamp, correlation ID, reason code.
- Worker: workflow execution ID, invocation ID, stage, attempt, duration, typed outcome, subject to cardinality controls.

## Prohibited by default

Never log API keys, bearer tokens, cookies, authorization headers, private keys, signed URLs or environment dumps; raw source files/diffs/full ADR or spec excerpts; full prompts/responses; unredacted PII/secrets; raw SQL parameters or DB credentials; unfiltered provider exception bodies that may include request data; unbounded model/tool input or private chain-of-thought.

If troubleshooting requires content, use a separately approved access-controlled artifact/transcript mechanism with explicit retention and audit access. Emit only its opaque reference and digest in normal logs. Redact at the boundary and test the redactor.

## Correlation and privacy

- Generate request/correlation IDs at trusted ingress when absent. Validate caller-provided correlation IDs and treat them only as metadata.
- Propagate trace context across HTTP/gRPC and workers. Trace/correlation IDs are not authorization.
- Workspace/job/source identifiers in logs are subject to retention/access policy.
- Never use user IDs, job IDs, artifact IDs, request IDs, prompt text or source paths as metric labels.
- Use service name, environment, operation, stage, bounded result, provider and error code as metric dimensions.
- Do not propagate secrets, source text or prompts as trace baggage.

## Stable event names

Suggested event names: api.request.completed; analysis.job.accepted; analysis.job.state_changed; analysis.stage.started; analysis.stage.completed; analysis.stage.failed; evidence.package.validated; model.run.started; model.run.completed; model.run.validation_failed; finding.created; finding.validation_failed; review.dispositioned; publication.attempted; publication.completed.

Event names are schema, not free-form prose. Add fields compatibly and version event schema if meaning changes.

## First-pass metrics and alerts

Request count/latency/error rate by operation and bounded status; job queue age, end-to-end duration, stage duration, retries, cancellations and terminal failures; evidence count and invalid/stale rate; model request latency/tokens/estimated cost/throttling/schema failures/refusals; findings by outcome/severity/review requirement; source freshness failures, idempotency conflicts, DB pool saturation, Lambda/workflow throttles and backlog.

Alert only on actionable thresholds set after baselines. Do not dashboard high-cardinality IDs.

## AuditEvent minimum schema

AuditEvent fields: auditEventId, schemaVersion, occurredAt, workspaceId, actorType, actorId or service principal, action, targetKind, targetId, optional targetVersion, outcome, safe reasonCode, optional requestId/correlationId/traceId, and allowlisted bounded attributes.

Write at the business transaction boundary or use a transactional outbox for coordinated effects. Audit attributes must not be an arbitrary request dump. Reviewer rationale may be sensitive and must follow review access policy. Define retention, integrity protection and export before production.

## Error and retry telemetry

Log a stable error category: INVALID_ARGUMENT, UNAUTHENTICATED, PERMISSION_DENIED, NOT_FOUND, CONFLICT, RATE_LIMITED, DEADLINE_EXCEEDED, DEPENDENCY_UNAVAILABLE, VALIDATION_FAILED, INTERNAL. Include retryable and attempt fields. Do not blindly retry authorization, schema or deterministic validation errors. Cap attempts, elapsed time and spend.

## Minimum observability tests

- seeded fake credentials never appear in captured logs;
- source snippets/prompts are not logged by default;
- required envelope fields exist;
- trace context propagates where supported;
- metrics contain no job/artifact/request IDs;
- audit records preserve actor, exact target version, action and disposition;
- provider exception bodies are redacted before logging.
`;export{e as default};
