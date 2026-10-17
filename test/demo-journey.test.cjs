const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const component = fs.readFileSync(path.join(__dirname, "../src/components/DemoExplorer.jsx"), "utf8");
const styles = fs.readFileSync(path.join(__dirname, "../src/styles.css"), "utf8");

test("guided ADR journey explains the investigation in five plain-language steps", () => {
  for (const phrase of [
    "Watch investigation",
    "In plain English",
    "Which parts of the system are in scope?",
    "What does the implementation actually say?",
    "The values do not line up.",
    "YOUR REVIEW",
    "Nothing was written to production.",
  ]) assert.ok(component.includes(phrase), "missing guided journey content: " + phrase);
  assert.ok(component.includes("const stepNames = ['Decision', 'Scope', 'Evidence', 'Assessment', 'Review']"));
});

test("guided journey supports manual navigation, playback, and accessible progress", () => {
  assert.ok(component.includes("setTimeout(() => setActiveStage(activeStage + 1), 4200)"));
  assert.ok(component.includes('aria-live="polite"'));
  assert.ok(component.includes("aria-current={index === activeStage ? 'step' : undefined}"));
  assert.ok(component.includes("onClick={() => goToStage(activeStage - 1)}"));
  assert.ok(component.includes("YOUR REVIEW"));
});

test("journey animations respect reduced-motion preferences and narrow screens", () => {
  assert.ok(styles.includes("@media (prefers-reduced-motion: reduce)"));
  assert.ok(styles.includes("@media (max-width: 760px)"));
  assert.ok(styles.includes("@keyframes journey-scene-enter"));
});
