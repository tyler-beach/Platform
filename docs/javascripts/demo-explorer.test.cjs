const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "demo-explorer.js"), "utf8");
const context = { URL, Date, Math, Array, Object, Number, String, Promise, console, document: undefined };
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "demo-explorer.js" });
const core = context.ADRDemoCore;

test("normalizes only known public run URLs and safe primitive metadata", () => {
  const rows = core.normalizeRuns([{ id: 42, run_number: 8, run_attempt: 1, name: "PoC <img>", event: "workflow_dispatch", status: "completed", conclusion: "success", head_branch: "main", head_sha: "a".repeat(40), html_url: "https://github.com/tyler-beach/Platform/actions/runs/42" }]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].name, "PoC <img>");
  assert.equal(rows[0].url, "https://github.com/tyler-beach/Platform/actions/runs/42");
  assert.equal(core.normalizeRuns([{ id: 43, html_url: "https://evil.example/steal" }]).length, 0);
});

test("normalizes jobs and orders steps by their numeric sequence", () => {
  const jobs = core.normalizeJobs([{ id: 5, name: "Analyze", status: "completed", conclusion: "success", html_url: "https://github.com/tyler-beach/Platform/runs/5/job/5", steps: [{ number: 2, name: "Later", status: "completed", conclusion: "success" }, { number: 1, name: "First", status: "completed", conclusion: "success" }] }]);
  assert.equal(jobs.length, 1);
  assert.deepEqual(Array.from(jobs[0].steps, step => step.number), [1, 2]);
});

test("uses bounded GitHub endpoints without browser credentials and exposes API failure", async () => {
  let captured;
  const fetcher = async (url, options) => {
    captured = { url, options };
    return { ok: false, status: 403, headers: { get: name => name === "x-ratelimit-reset" ? "123" : null } };
  };
  await assert.rejects(core.fetchWorkflowRuns(fetcher, "poc-analysis.yml"), /rate limit/);
  assert.match(captured.url, /api\.github\.com\/repos\/tyler-beach\/Platform\/actions\/workflows\/poc-analysis\.yml\/runs\?per_page=10/);
  assert.equal(captured.options.credentials, "omit");
  assert.equal("Authorization" in captured.options.headers, false);
});

test("uses the selected attempt for jobs and reports malformed API payloads", async () => {
  let captured;
  const jobs = await core.fetchRunJobs(async (url) => {
    captured = url;
    return { ok: true, json: async () => ({ jobs: [] }) };
  }, { id: 53, attempt: 2 });
  assert.match(captured, /actions\/runs\/53\/attempts\/2\/jobs\?per_page=100/);
  assert.equal(jobs.length, 0);
  await assert.rejects(core.fetchWorkflowRuns(async () => ({ ok: true, json: async () => ({ workflow_runs: "bad" }) }), "poc-analysis.yml"), /malformed run history/);
});

test("ignores malformed jobs and never returns API-provided script URLs", () => {
  const jobs = core.normalizeJobs([{ id: "bad", name: "<script>run()</script>", html_url: "javascript:alert(1)", steps: [] }]);
  assert.deepEqual(Array.from(jobs), []);
});

test("supports a private organization clone while rejecting another repository", () => {
  const repository = "example-org/adr-platform";
  const rows = core.normalizeRuns([{
    id: 77, run_number: 9, status: "completed", html_url: `https://github.com/${repository}/actions/runs/77`,
  }], repository);
  assert.equal(rows.length, 1);
  assert.equal(core.normalizeRuns([{
    id: 78, run_number: 10, status: "completed", html_url: "https://github.com/tyler-beach/Platform/actions/runs/78",
  }], repository).length, 0);
});

test("uses the cloned repository for anonymous history requests without accepting arbitrary names", async () => {
  let captured;
  const fetcher = async (url) => {
    captured = url;
    return { ok: true, json: async () => ({ workflow_runs: [] }) };
  };
  await core.fetchWorkflowRuns(fetcher, "poc-analysis.yml", "example-org/adr-platform");
  assert.match(captured, /api\.github\.com\/repos\/example-org\/adr-platform\//);
  await core.fetchWorkflowRuns(fetcher, "poc-analysis.yml", "evil.example/attacker");
  assert.match(captured, /api\.github\.com\/repos\/tyler-beach\/Platform\//);
});
