const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const read = relative => fs.readFileSync(path.join(root, relative), "utf8");

test("pod disruption budget ADR states a language-neutral availability invariant", () => {
  const adr = read("docs/adr/POD-DISRUPTION-BUDGETS.md");
  assert.match(adr, /workloads classified as availability-sensitive/i);
  assert.match(adr, /disruption budget/i);
  assert.match(adr, /replica topology/i);
  assert.match(adr, /inconclusive/i);
  assert.doesNotMatch(adr, /MUST use (?:Go|Python|Java|JavaScript|TypeScript)/i);
});

test("session TTL ADR defines a 60-minute absolute maximum and renewal semantics", () => {
  const adr = read("docs/adr/SESSION-TTL.md");
  assert.match(adr, /MUST be 60 minutes/i);
  assert.match(adr, /absolute maximum/i);
  assert.match(adr, /MUST NOT extend the lifetime of the existing session/i);
  assert.match(adr, /renewal/i);
  assert.match(adr, /inconclusive/i);
});

test("interactive workspace connects decision, evidence, stage trace, and local review", () => {
  const component = read("src/components/DemoExplorer.jsx");
  const styles = read("src/styles.css");
  for (const phrase of ["DECISION → IMPLEMENTATION", "EVIDENCE TRAIL", "OBSERVED STATE", "CANDIDATE FINDING", "Nothing was written to production"]) {
    assert.ok(component.includes(phrase), `missing UI contract: ${phrase}`);
  }
  assert.match(component, /aria-selected=\{activeKey === item\.key\}/);
  assert.match(component, /handleTabKeyDown/);
  assert.match(component, /event\.key === 'ArrowRight'/);
  assert.match(component, /role="tabpanel" aria-labelledby/);
  assert.match(component, /SYNTHETIC REF/);
  assert.match(component, /aria-pressed=\{activeEvidence === item\.id\}/);
  assert.match(styles, /@media \(max-width: 600px\)/);
});
