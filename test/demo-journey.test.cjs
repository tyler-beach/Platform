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
  ]) assert.ok(component.includes(phrase), \`missing guided journey content: \${phrase}\`);
  assert.match(component, /const stepNames = \['Decision', 'Scope', 'Evidence', 'Assessment', 'Review'\]/);
});

test("guided journey supports manual navigation, playback, and accessible progress", () => {
  assert.match(component, /setTimeout\(\(\) => setActiveStage\(activeStage \+ 1\), 4200\)/);
  assert.match(component, /aria-live="polite"/);
  assert.match(component, /aria-current={index === activeStage \? 'step' : undefined}/);
  assert.match(component, /onClick=\{\(\) => goToStage\(activeStage - 1\)\}/);
  assert.match(component, /onClick=\{\(\) => \{ if \(activeStage === example\.stages\.length - 1\)/);
});

test("journey animations respect reduced-motion preferences and narrow screens", () => {
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.journey-lab/);
  assert.match(styles, /@media \(max-width: 760px\)[\s\S]*?\.journey-workspace/);
  assert.match(styles, /@keyframes journey-scene-enter/);
});
