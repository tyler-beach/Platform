# Go-first implementation and tooling

## Language strategy
Go is the primary language for APIs, deterministic workers, orchestration adapters, persistence, gRPC server/client and the AI harness. Python may be used behind a clear worker/API boundary if a required parser/evaluation library is materially better and cannot reasonably be used from Go. Avoid splitting the service language by default.

## Candidate stack
| Concern | Candidate | Notes |
|---|---|---|
| Language | Go | Pin toolchain in go.mod and CI when implementation begins. |
| RPC API | gRPC-Go + Protocol Buffers | Versioned contract in proto/; generated clients/server stubs. |
| Schema tooling | Buf CLI | Format, lint, build, generate, detect breaking changes. |
| Code generation | protoc-gen-go and protoc-gen-go-grpc | Pin generator versions. |
| Anthropic | Official anthropic-sdk-go | Direct API, not Bedrock. |
| Lambda | aws-lambda-go | Reusable worker entry points. |
| AWS APIs | AWS SDK for Go v2 | S3, Secrets Manager and other AWS calls. |
| Workflow | AWS Step Functions | Top-level distributed job lifecycle. |
| Database | pgx + PostgreSQL/Aurora | Migrations and typed queries. |
| Logging | log/slog | job, stage, trace, attempt and status fields. |
| Tracing | OpenTelemetry Go | Trace ingress, orchestration boundaries and model calls. |
| Code parsing | Tree-sitter + language-specific parser/compiler tooling | Select languages based on pilot. |
| Tests | Go tests + integration/evaluation fixtures | Mock provider APIs in deterministic unit tests. |
| IaC | Terraform candidate | Organization standard remains open. |
| CI | GitHub Actions candidate | Tests, scans, OpenSpec and Buf compatibility checks. |

References: https://github.com/anthropics/anthropic-sdk-go ; https://grpc.io/docs/languages/go/quickstart/ ; https://buf.build/docs/generate/tutorial/ ; https://opentelemetry.io/docs/languages/go/

## Suggested repository layout
~~~text
cmd/
  grpc-api/
  api-http/                 # optional webhook/REST adapter
  workers/
internal/
  domain/
  artifacts/
  evidence/
  retrieval/
  analysis/
  ai/anthropic/
  transport/grpc/
  transport/http/
  orchestration/
  persistence/
  observability/
proto/adrplatform/v1/
gen/go/                     # generated; commit/build policy to be decided
workflows/
infra/terraform/
openspec/
tests/integration/
tests/evaluations/
~~~

This is a target layout, not a mandate to create empty packages. A modular Go codebase can have multiple Lambda entry points and one separate long-lived gRPC API binary.

## Contract-first workflow
1. Edit the versioned .proto contract.
2. Run buf format, buf lint and buf build.
3. Run buf breaking against the target compatibility baseline.
4. Generate Go messages and gRPC stubs using checked-in buf.gen.yaml.
5. Implement transport handlers that map generated transport DTOs to internal domain types.
6. Test RPC behavior, auth and compatibility.
7. Regenerate and verify there is no unexpected diff.

Do not manually edit generated files. Pin Buf and generator/plugin versions in CI or the tool version file before relying on reproducible code generation.

## Code organization
Use ports/adapters to keep domain behavior independent from AWS, Postgres and provider request types. Pass context.Context through I/O boundaries. Propagate deadlines/cancellation across RPC. Map internal errors to a documented gRPC status contract at the transport layer. Do not treat caller-supplied workspace ID as authorization. Use idempotency for job creation. Keep message-size limits and page-size caps.

Useful interfaces at genuine boundaries include ArtifactRepository, DecisionRepository, EvidenceRetriever, StaticAnalyzer, ModelAssessor, FindingRepository, JobRepository and WorkflowStarter. Avoid interfaces for every concrete type.

## Lambda and Protobuf boundary
Lambda workers are invoked by Step Functions using AWS-native integration and a JSON envelope. If Protobuf types are reused in workflow input/output, use protojson and integration tests; the workflow should carry small IDs/references, not whole documents or binary Protobuf payloads. gRPC is for a running server, not for an ordinary short-lived Lambda handler.

## CI baseline
- gofmt, go vet, tests and static analysis.
- dependency/secret scanning.
- buf lint/build; buf breaking on PRs.
- generated-code consistency check once generated files are in repository.
- OpenSpec validation.
- Integration tests for gRPC authorization, timeouts, idempotency and schema compatibility.
- Labeled evaluation regression for retrieval, prompts and findings.

Use fixtures/mocks for deterministic unit tests; do not require live Anthropic calls on every test run.

## Code analysis caution
Go parser tooling does not solve multi-language analysis. Tree-sitter gives syntax; semantic resolution may require compiler APIs, language servers, build metadata or static-analysis systems. A parse is not proof of runtime behavior.
