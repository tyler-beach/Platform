const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const demoIndex = fs.readFileSync(path.join(__dirname, "../docs/demo/index.md"), "utf8");
const spec = fs.readFileSync(path.join(__dirname, "../docs/demo/realistic-session-service.md"), "utf8");
const api = fs.readFileSync(path.join(__dirname, "../docs/demo/api-payload-examples.md"), "utf8");
const review = fs.readFileSync(path.join(__dirname, "../docs/demo/finding-review-playbook.md"), "utf8");
const lineage = fs.readFileSync(path.join(__dirname, "../docs/demo/evidence-lineage-example.md"), "utf8");
const component = fs.readFileSync(path.join(__dirname, "../src/components/DemoExplorer.jsx"), "utf8");
const openapi = fs.readFileSync(path.join(__dirname, "../docs/openapi.yaml"), "utf8");
const apiContract = fs.readFileSync(path.join(__dirname, "../docs/contracts/API_CONTRACT.md"), "utf8");

test("demo index exposes the multi-requirement specification, API mockups, and review guide", () => {
  assert.ok(demoIndex.includes("realistic-session-service.md"));
  assert.ok(demoIndex.includes("api-payload-examples.md"));
  assert.ok(demoIndex.includes("finding-review-playbook.md"));
  assert.ok(demoIndex.includes("evidence-lineage-example.md"));
  assert.ok(demoIndex.includes("production target"));
});

test("technical specification includes mixed outcomes and evidence limits", () => {
  for (const requirement of ["SES-001", "SES-002", "SES-003", "SES-004", "SES-005", "SES-006", "SES-007", "SES-008", "SES-009", "SES-010"]) {
    assert.ok(spec.includes(requirement), "missing requirement " + requirement);
  }
  for (const phrase of ["Potential deviation", "Inconclusive", "minAvailable: 2", "riskClient.score()", "does not prove an outage", "human verification required"]) {
    assert.ok(spec.toLowerCase().includes(phrase.toLowerCase()), "missing technical scenario detail: " + phrase);
  }
  assert.ok(spec.includes("fnd_ses_005_pdb_minavailable"));
  assert.ok(spec.includes("evidenceRefs"));
});

test("API mockups use the production-target contract enums and response shapes", () => {
  for (const phrase of [
    "HTTP 202 Accepted",
    "ANALYSIS_JOB_STATUS_QUEUED",
    "ANALYSIS_JOB_STATUS_SUCCEEDED",
    "FINDING_OUTCOME_DEVIATION_SUPPORTED",
    "FINDING_OUTCOME_INCONCLUSIVE",
    "FINDING_SEVERITY_HIGH",
    "REVIEW_STATUS_PENDING",
    "IDEMPOTENCY_KEY_REUSED",
    "nextPageToken",
    "reusedExistingJob"
  ]) assert.ok(api.includes(phrase), "missing API mock detail: " + phrase);
  assert.ok(api.includes("Mock API responses"));
  assert.ok(api.includes("not responses captured from a running service"));
  assert.ok(api.includes("proto/adrplatform/v1/platform.proto"));
  assert.ok(!api.includes("JOB_STATE_QUEUED"));
  assert.ok(!api.includes("FINDING_OUTCOME_SUPPORTED_DEVIATION"));
});

test("finding review playbook separates evidence, inference, outcome, and human disposition", () => {
  for (const phrase of [
    "Deviation supported",
    "Potential finding",
    "Inconclusive",
    "not calibrated probabilities",
    "Pin the inputs",
    "Challenge the inference",
    "Not established",
    "reviewer identity",
    "synthetic artifacts"
  ]) assert.ok(review.toLowerCase().includes(phrase.toLowerCase()), "missing review guidance: " + phrase);
});

test("evidence lineage walkthrough demonstrates pinned inputs and review audit separation", () => {
  for (const phrase of [
    "Synthetic fixture",
    "artifactVersionId",
    "locatorPrecision",
    "relationToClaim",
    "FINDING_OUTCOME_DEVIATION_SUPPORTED",
    "evidence package",
    "reviewer disposition",
    "RUNTIME_CONTEXT_REQUIRED",
    "Missing evidence means inconclusive"
  ]) assert.ok(lineage.toLowerCase().includes(phrase.toLowerCase()), "missing lineage detail: " + phrase);
  assert.ok(lineage.includes("../contracts/EVIDENCE.md"));
  assert.ok(lineage.includes("../contracts/LOGGING_AND_AUDIT.md"));
});

test("interactive demo labels and renders a contract-shaped mock API response", () => {
  assert.ok(component.includes("MOCK RESPONSE · application/json"));
  assert.ok(component.includes("HTTP 200"));
  assert.ok(component.includes("FINDING_OUTCOME_DEVIATION_SUPPORTED"));
  assert.ok(component.includes("production-target contract"));
  assert.ok(component.includes("demo/evidence-lineage-example/"));
  assert.ok(component.includes("Separate the machine-generated finding from the human review event"));
});

test("API docs describe the production target without claiming the service is deployed", () => {
  assert.ok(openapi.includes("version: 1.0.0"));
  assert.ok(openapi.includes("Production-target REST/JSON mapping"));
  assert.ok(apiContract.includes("Production-target v1 contract"));
  assert.ok(apiContract.includes("rather than a deployed service"));
});
