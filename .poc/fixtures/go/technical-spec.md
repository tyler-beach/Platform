# Technical Specification: Request Processing

## Requirement RQ-17 — Non-blocking provider assessment

The request handler must enqueue provider assessment asynchronously and return without waiting for the remote provider response. Synchronous or inline provider calls before the handler returns are prohibited.

## Requirement RQ-18 — Evidence

The implementation must preserve a traceable source path from the request handler to any provider call. If static analysis cannot resolve the dispatch target, the result must remain inconclusive or identify the unresolved call path.
