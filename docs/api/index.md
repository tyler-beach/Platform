# API reference

Interactive Swagger UI for the **proposed REST/JSON v1 façade**. The source typed control-plane contract is Protobuf in the repository.

> **Status: design-only.** No production HTTP base URL or deployed service is implied. Swagger request execution is disabled by default because a compatible server and authentication are not deployed by this project yet.

<div id="swagger-ui"></div>

<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
<script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
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
</script>

## Related contracts

- [API behavior, lifecycle, errors and versioning](../contracts/API_CONTRACT.md)
- [Data types and invariants](../contracts/CONTRACTS.md)
- [Evidence and provenance](../contracts/EVIDENCE.md)
- [Logging, tracing, metrics and audit](../contracts/LOGGING_AND_AUDIT.md)
- [Raw OpenAPI file](../openapi.yaml)
- [Protobuf schema](https://github.com/tyler-beach/Platform/blob/main/proto/adrplatform/v1/platform.proto)

Artifact ingestion, review submission, decision management, audit querying and evidence excerpt download are intentionally omitted from this first public API.
