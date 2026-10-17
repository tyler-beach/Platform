const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const demoIndex = fs.readFileSync(path.join(__dirname, "../docs/demo/index.md"), "utf8");
const spec = fs.readFileSync(path.join(__dirname, "../docs/demo/realistic-session-service.md"), "utf8");
const api = fs.readFileSync(path.join(__dirname, "../docs/demo/api-payload-examples.md"), "utf8");

test("demo index exposes the multi-requirement specification and API payload examples", () => {
  assert.ok(demoIndex.includes("realistic-session-service.md"));
  assert.ok(demoIndex.includes("api-payload-examples.md"));
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

test("API examples show async acceptance, findings, inconclusive state, and stable errors", () => {
  for (const phrase of ["HTTP 202", "JOB_STATE_QUEUED", "JOB_STATE_SUCCEEDED", "FINDING_OUTCOME_SUPPORTED_DEVIATION", "FINDING_OUTCOME_INCONCLUSIVE", "IDEMPOTENCY_KEY_REUSED", "requestId", "nextPageToken"]) {
    assert.ok(api.includes(phrase), "missing API payload detail: " + phrase);
  }
  assert.ok(api.includes("no production HTTP service is deployed"));
  assert.ok(api.includes("proto/adrplatform/v1/platform.proto"));
});
