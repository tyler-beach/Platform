const e=`# API reference

Interactive Swagger UI for the **Pathfinder production-target REST/JSON v1 contract**. The typed control-plane contract is Protobuf in the repository; this OpenAPI document defines its REST mapping.

> **Implementation status:** contract and mock response examples are available for production implementation. A live API server and authentication are not deployed by this documentation site, so Swagger request execution is disabled by default.

<div id="swagger-ui"></div>

<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
<script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"><\/script>
<script>
window.addEventListener("load", function () {
  if (window.SwaggerUIBundle) {
    window.SwaggerUIBundle({
      url: "../openapi.yaml",
      dom_id: "#swagger-ui",
      deepLinking: true,
      displayRequestDuration: true,
      tryItOutEnabled: false,
      presets: [window.SwaggerUIBundle.presets.apis],
      layout: "BaseLayout"
    });
  }
});
<\/script>

## Mock response examples

- [Production-target API response mockups](../demo/api-payload-examples.md) — HTTP 202 job acceptance, lifecycle polling, evidence-linked findings, inconclusive outcome, and 409 idempotency conflict.
- [API behavior, lifecycle, errors and versioning](../contracts/API_CONTRACT.md)
- [Data types and invariants](../contracts/CONTRACTS.md)
- [Evidence and provenance](../contracts/EVIDENCE.md)
- [Logging, tracing, metrics and audit](../contracts/LOGGING_AND_AUDIT.md)
- [Raw OpenAPI file](../openapi.yaml)
- [Protobuf schema](https://github.com/tyler-beach/Platform/blob/main/proto/adrplatform/v1/platform.proto)

Artifact ingestion, review submission, decision management, audit querying and evidence excerpt download are intentionally outside the initial API surface.
`;export{e as default};
