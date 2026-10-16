# Change: introduce gRPC and Protobuf contracts

## Why
The platform needs explicit, versioned service contracts for Go clients and future service boundaries, while the analysis workflow stays asynchronous and cloud-orchestrated.

## Proposed change
Adopt Protocol Buffers as the source schema for a versioned platform API and use gRPC for synchronous job-control operations where a long-lived Go server is justified. Keep Step Functions as the owner of distributed analysis execution and invoke Lambda workers directly. Define the initial API schema and Buf configuration.

## Scope
- A versioned adrplatform.v1 Protobuf contract for create/get/cancel job and list/get finding operations.
- Buf workspace, lint, breaking-change and generation configuration.
- Guidance for gRPC hosting, worker boundaries, errors, versioning and operational constraints.
- Architecture/OpenSpec guidance that makes the division between RPC and workflow explicit.

## Non-goals
- Implementing the production gRPC server or authorization middleware in this change.
- Generated .pb.go code before a pinned toolchain is available and generation is verified.
- gRPC listeners inside Lambda workers.
- Replacing Step Functions with gRPC orchestration.
- Defining every future worker RPC before a real service boundary exists.

## Acceptance criteria
- Schema has explicit enums, versioned package, immutable artifact references, job lifecycle and evidence-backed finding messages.
- Job creation is asynchronous and does not keep an RPC open for complete analysis.
- Documentation distinguishes gRPC, Protobuf, Step Functions and Lambda responsibilities.
- Buf configuration supports lint/build/generation and breaking-change detection.
- Open questions state whether a long-lived gRPC API is justified for the MVP.
- No claim is made that server code, generated code, infrastructure or validation is complete.
