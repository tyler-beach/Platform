# Go-first implementation and tooling

## Language strategy
Go is the primary application language for API, workers, deterministic analysis, persistence, orchestration adapters and the AI harness. Python may be used behind an explicit worker/API boundary if a specific parser or evaluation library is materially better and cannot reasonably be consumed from Go. Avoid a split-language architecture by default.

## Candidate stack
| Concern | Candidate | Notes |
|---|---|---|
| Language | Go | Pin toolchain in go.mod/CI when implementation starts. |
| Anthropic | Official anthropic-sdk-go | Direct API, not Bedrock. |
| Lambda | aws-lambda-go | Reusable worker entry points. |
| AWS APIs | AWS SDK for Go v2 | IAM, S3, secrets and other AWS calls. |
| Workflow | AWS Step Functions | Top-level distributed state owner. |
| PostgreSQL | pgx | Typed data access and migrations. |
| Logging | log/slog | Structured fields incl. job, stage, trace and attempt IDs. |
| Tracing | OpenTelemetry Go | Trace ingress through worker and model calls. |
| Code parsing | Tree-sitter + language-specific parsers/compiler tooling | Pick target languages based on pilot. |
| Testing | Go testing + fixtures + integration/evaluation suites | Mock model API in deterministic unit tests. |
| IaC | Terraform candidate | Team standard remains an open question. |
| CI | GitHub Actions candidate | Lint, tests, scans, OpenSpec validation and builds. |

References: https://github.com/anthropics/anthropic-sdk-go ; https://opentelemetry.io/docs/languages/go/ ; https://docs.aws.amazon.com/lambda/latest/dg/with-step-functions.html

## Suggested repository layout
~~~text
cmd/
  api/
  ingest/
  analyze-code/
  analyze-documents/
  retrieve-context/
  assess-deviation/
  verify-findings/
internal/
  domain/ artifacts/ evidence/ retrieval/ analysis/
  ai/anthropic/ ai/prompts/ ai/schemas/
  orchestration/ persistence/ observability/
migrations/
workflows/
infra/terraform/
openspec/
tests/integration/
tests/evaluations/
~~~
This is a target structure, not a mandate to create empty packages. Prefer a modular Go codebase with multiple Lambda entry points over premature microservices.

## Code organization
Use ports/adapters to isolate domain behavior from AWS, PostgreSQL and Anthropic. Pass context.Context through I/O boundaries; define explicit deadlines. Avoid global mutable state. Use typed enums for finding/job states, version worker payload contracts, and introduce interfaces at real dependency boundaries rather than for every struct.

Useful interfaces may include ArtifactRepository, DecisionRepository, EvidenceRetriever, StaticAnalyzer, ModelAssessor, FindingRepository and JobRepository.

## CI baseline
1. gofmt and go vet.
2. Unit tests, integration tests and race checks where useful.
3. Static analysis/lint, dependency scanning and secret scanning.
4. OpenSpec validation.
5. Build/package tests for each Lambda target.
6. Regression evaluation for retrieval, prompts, schemas, or finding semantics.
Do not require a live model call for every unit test; use fixtures/mocks and a smaller scheduled or gated live evaluation set.

## Language/tooling caution
The service reads multiple target languages; Go's own parser does not solve that problem. Tree-sitter gives syntax, while semantic resolution may require compiler APIs, language-server output, build metadata or static-analysis tools. A successful parse is not proof of runtime behavior.
