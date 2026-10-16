# Tools and primary references

Re-check versions and terms at implementation time.

## Anthropic
- Go SDK: https://github.com/anthropics/anthropic-sdk-go
- API overview: https://platform.claude.com/docs/en/api/overview
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs

Call Anthropic directly, as specified. Keep request/response types behind a narrow adapter.

## AWS
- Step Functions with Lambda: https://docs.aws.amazon.com/lambda/latest/dg/with-step-functions.html
- Step Functions parallel state: https://docs.aws.amazon.com/step-functions/latest/dg/state-parallel.html
- AWS SDK for Go v2: https://aws.github.io/aws-sdk-go-v2/docs/

## OpenSpec
- Setup: https://openspec.dev/docs/setup
- Quickstart: https://openspec.dev/docs/quickstart
- CLI: https://openspec.dev/docs/cli
- Project configuration: https://openspec.dev/docs/configuration/config-yaml
- Spec-driven schema: https://openspec.dev/docs/schemas/spec-driven

Prefer the official current guide and installed CLI output. Workflow names/features can change.

## Other
- OpenTelemetry Go: https://opentelemetry.io/docs/languages/go/
- Go testing: https://pkg.go.dev/testing
- Tree-sitter: https://tree-sitter.github.io/tree-sitter/

These are reference links, not blanket endorsements of all features. Assess maintenance, license, security, operational burden and measured benefit before adding a dependency.
