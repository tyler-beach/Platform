# Tools and primary references

Re-check versions and terms when implementation begins.

## gRPC and Protobuf
- gRPC Go quickstart: https://grpc.io/docs/languages/go/quickstart/
- gRPC generated code reference: https://grpc.io/docs/languages/go/generated-code/
- Buf generation: https://buf.build/docs/generate/tutorial/
- Buf breaking-change detection: https://buf.build/docs/breaking/
- Protobuf API contract: proto/adrplatform/v1/platform.proto

Use Buf for schema formatting/lint/build/generation and compatibility detection. Pin tool/plugin versions before depending on reproducible generation.

## Anthropic
- Go SDK: https://github.com/anthropics/anthropic-sdk-go
- API overview: https://platform.claude.com/docs/en/api/overview
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs

Call Anthropic directly. Keep provider request/response types behind a narrow adapter.

## AWS
- Step Functions with Lambda: https://docs.aws.amazon.com/lambda/latest/dg/with-step-functions.html
- Step Functions parallel state: https://docs.aws.amazon.com/step-functions/latest/dg/state-parallel.html
- ALB gRPC target groups: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- AWS SDK for Go v2: https://aws.github.io/aws-sdk-go-v2/docs/

The ALB gRPC target group target types are instance/IP, not Lambda. A gRPC listener therefore needs a long-lived service; Step Functions should call Lambda natively.

## OpenSpec
- Setup: https://openspec.dev/docs/setup
- CLI: https://openspec.dev/docs/cli
- Project configuration: https://openspec.dev/docs/configuration/config-yaml
- Spec-driven schema: https://openspec.dev/docs/schemas/spec-driven

Prefer the official current guide and installed CLI output; command names/features can change.

## Observability and testing
- OpenTelemetry Go: https://opentelemetry.io/docs/languages/go/
- Go testing: https://pkg.go.dev/testing
- Tree-sitter: https://tree-sitter.github.io/tree-sitter/

These links are starting points, not endorsements of every feature. Evaluate maintenance, license, security, operational cost and measured benefit before adding dependencies.
