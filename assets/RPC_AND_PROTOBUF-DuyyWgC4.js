const e=`# gRPC and Protocol Buffers integration

## Recommendation

Adopt contract-first Protocol Buffers for the platform's stable RPC API and shared typed request/response contracts. Use gRPC for synchronous request/response at the service boundary, while keeping AWS Step Functions as the owner of asynchronous analysis workflow and invoking Lambda workers directly.

This is a deliberate hybrid:
- gRPC is the communication protocol for callers that need typed, synchronous operations on the platform API.
- Protobuf is the versioned schema from which Go types and gRPC stubs are generated.
- Step Functions owns multi-stage job state, branching, retry, timeout and completion.
- Lambda workers do bounded tasks and do not run gRPC servers.
- If a future worker becomes a long-lived service, gRPC can be used at that service boundary when there is a measured need.

Do not make every Lambda a gRPC server. AWS Application Load Balancer gRPC target groups require instance/IP targets and cannot target Lambda functions. A gRPC server therefore belongs in a long-lived process, for example a Go container service on ECS/Fargate behind an HTTPS ALB. See the official ALB target group protocol documentation: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html

## Logical topology

~~~mermaid
flowchart TB
  Clients["Go clients / internal platform consumers"]
  ALB["HTTPS Application Load Balancer\\nHTTP/2 + gRPC"]
  API["Go gRPC API service\\nECS/Fargate (optional deployment profile)"]
  AUTH["AuthN/AuthZ + request validation"]
  DB[("Aurora PostgreSQL\\njobs, findings, metadata")]
  SF["AWS Step Functions\\njob lifecycle"]
  L1["Go Lambda\\nnormalize / ingest"]
  L2["Go Lambda\\nretrieve context"]
  L3["Go Lambda\\nstatic analysis"]
  L4["Go Lambda\\nAnthropic assessment"]
  L5["Go Lambda\\nverify / persist"]
  A["Anthropic API directly"]
  S3[("S3\\nversioned artifacts as needed")]
  Clients --> ALB --> API --> AUTH
  AUTH --> DB
  API --> SF
  SF --> L1
  SF --> L2
  SF --> L3
  SF --> L4
  L4 --> A
  SF --> L5
  L1 --> DB
  L2 --> DB
  L3 --> S3
  L5 --> DB
~~~

The API starts, queries and cancels jobs; it does not perform full analysis inline. The state machine invokes bounded worker tasks using AWS integrations. The gRPC API should return a job ID promptly, not hold an RPC open for the entire analysis.

## Where gRPC belongs

### Good fit
- A stable API called by multiple Go services or internal tools.
- Strong request/response contracts and generated clients.
- Synchronous job creation, job status lookup, cancellation, or paginated finding retrieval.
- A service boundary deployed as a long-lived server.

### Not a default fit
- Step Functions invoking Lambda workers: use native AWS service integration.
- A Lambda worker that performs one task and exits: do not make it host a gRPC listener.
- High-latency whole-analysis requests: create an asynchronous job and return a job ID.
- Browser or third-party webhook clients that naturally speak HTTP/JSON: provide a separate adapter only if required; do not force gRPC on every consumer.

If the first release only needs GitHub webhooks and an async Lambda pipeline, the simplest system may skip a long-running gRPC endpoint while still defining Protobuf contracts. Add the ECS/Fargate gRPC API only when there is a real synchronous RPC consumer. This trades always-on capacity/ALB/networking for an explicit service API.

## API operations

The initial contract in proto/adrplatform/v1/platform.proto defines DeviationPlatformService:
- CreateAnalysisJob — validate immutable input references, create an idempotent job and start the Step Functions execution. Return job identity/status, not final findings.
- GetAnalysisJob — report job state and basic metadata.
- CancelAnalysisJob — request cancellation where the current workflow state permits it.
- ListFindings — return paginated finding records.
- GetFinding — return one finding and its validated evidence references.

Do not send megabytes of source in an RPC. Upload content or point to authorized immutable source versions and submit artifact references plus hashes.

## Protobuf contracts and versioning

- Use a package path such as adrplatform.v1; keep service/message names stable.
- Assign field numbers once; never reuse a removed field number or name. Reserve removed fields.
- Add optional fields compatibly; do not change an existing field's wire type or meaning.
- Use explicit enums with *_UNSPECIFIED = 0; define meaningful states, not overloaded booleans.
- Use google.protobuf.Timestamp for timestamps and documented units for numeric values.
- Keep protocol messages as transport contracts; map to domain types at service boundaries.
- Keep authenticated identity in verified request context/metadata. A caller-provided workspace_id is a selector, not proof of authorization.
- Handle unknown enum values and future fields defensively.
- Make breaking-change detection part of CI.

Use Buf for lint/build/generation/schema compatibility rather than hand-maintained protoc shell scripts. Official guide: https://buf.build/docs/generate/tutorial/. gRPC Go generation guide: https://grpc.io/docs/languages/go/quickstart/.

## Generation and repository policy

Schemas live in proto/. Configuration is checked in as buf.yaml and buf.gen.yaml. Developers install the Buf CLI and the Go plugins if local generation uses local plugins:

~~~sh
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
buf lint
buf breaking --against '.git#branch=main'
buf generate
~~~

The initial docs pass checks in schema and generator configuration but intentionally does not include generated .pb.go files because generation has not been run in this environment. Before application code imports generated packages, run generation in a Go-enabled checkout, pin plugin/tool versions, decide whether generated code is committed or generated in CI, and verify clean regeneration.

## Step Functions and Protobuf payloads

Step Functions uses JSON state input/output. Keep workflow state small: job IDs, artifact/version IDs, evidence object IDs, flags and stage outcomes. If a workflow message is represented as a Protobuf type, use protojson at the boundary and test field names/enums/default values round-trip. Do not put binary Protobuf wire bytes into state-machine JSON or pass large evidence text through every state. Store large evidence in S3/database and pass references.

A Protobuf schema does not force every internal message to use gRPC. Lambda event messages can use a documented JSON contract; the system can map to/from generated Protobuf types when shared contract governance is beneficial. Document each boundary's serialization explicitly.

## gRPC reliability and errors

- Propagate context, deadlines and cancellation.
- Set message-size limits and pagination limits.
- Use TLS; require identity/authentication and enforce workspace/repository authorization.
- Classify errors using standard gRPC status codes: INVALID_ARGUMENT, UNAUTHENTICATED, PERMISSION_DENIED, NOT_FOUND, ALREADY_EXISTS, RESOURCE_EXHAUSTED, DEADLINE_EXCEEDED, UNAVAILABLE and INTERNAL.
- Retry only safe, retryable calls; use idempotency keys for job creation.
- Do not automatically retry non-idempotent requests without idempotency semantics.
- Instrument latency, status code, trace ID and request/job ID; avoid logging full source or credentials.
- Health-check the service and define graceful shutdown.
- Set max receive/send sizes; use pagination rather than unbounded responses.

## Decision boundary

This is a recommended design pass, not a claim that a gRPC server, Fargate deployment, protobuf-generated Go code or RPC client already exists. See openspec/changes/grpc-protobuf-contracts/ for the proposed adoption and implementation tasks.
`;export{e as default};
