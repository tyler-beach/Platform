const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const component = fs.readFileSync(path.join(__dirname, "../src/components/DemoExplorer.jsx"), "utf8");
const styles = fs.readFileSync(path.join(__dirname, "../src/styles.css"), "utf8");
const plan = fs.readFileSync(path.join(__dirname, "../docs/DEMO_UX_IMPLEMENTATION_PLAN.md"), "utf8");

test("guided ADR journey explains the investigation in five plain-language steps", () => {
  for (const phrase of [
    "Watch an investigation",
    "In plain English",
    "Which parts of the system are in scope?",
    "What does the implementation actually say?",
    "The values do not line up.",
    "What it does not prove",
    "Your local choice:",
    "This walkthrough uses example data",
    "Example data only · no live systems checked",
  ]) assert.ok(component.includes(phrase), "missing guided journey content: " + phrase);
  assert.ok(component.includes("const stepNames = ['Decision', 'Scope', 'Evidence', 'Assessment', 'Review']"));
  assert.ok(component.includes("What this supports"));
  assert.ok(component.includes("No source excerpt supplied for this example"));
});

test("guided journey supports manual navigation, pause/resume, and accessible progress", () => {
  assert.ok(component.includes("setTimeout(() => setActiveStage(activeStage + 1), 7000)"));
  assert.ok(component.includes("Pause walkthrough"));
  assert.ok(component.includes("aria-live=\"polite\""));
  assert.ok(component.includes("aria-current={index === activeStage ? 'step' : undefined}"));
  assert.ok(component.includes("onClick={() => goToStage(activeStage - 1)}"));
  assert.ok(component.includes("aria-pressed={activeEvidence === item.id}"));
});

test("journey animations respect reduced-motion preferences and narrow screens", () => {
  assert.ok(styles.includes("@media (prefers-reduced-motion: reduce)"));
  assert.ok(styles.includes("@media (max-width: 760px)"));
  assert.ok(styles.includes("@keyframes journey-scene-enter"));
  assert.ok(styles.includes(".journey-selected-source__checks"));
});

test("the implementation plan keeps synthetic examples distinct from live PoC runs", () => {
  assert.ok(plan.includes("Synthetic walkthrough"));
  assert.ok(plan.includes("does not change the detection engine"));
  assert.ok(plan.includes("human review"));
});
