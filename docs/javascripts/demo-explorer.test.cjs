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

test("offers the Functional Analysis Demo workflow alongside the audit workflows", () => {
  assert.ok(core.workflows.some(workflow => workflow.id === "functional-analysis-demo.yml"));
});

test("renders ledger-only history without inventing unavailable job status", () => {
  const projection = core.historyProjection({
    schema_version: "adr-demo-history-v1", repository: "example-org/adr-platform",
    api_history_available: false, data_available: true, workflow_runs: [],
    runs: [{ github_run_id: 789, run_attempt: 1, workflow_url: "https://github.com/example-org/adr-platform/actions/runs/789",
      started_at: "2026-10-17T10:00:00Z", completed_at: "2026-10-17T10:01:00Z", comparison: "code-diff",
      language: "go", provider: "mock", status: "complete", outcome: "supported_deviation" }],
  }, "example-org/adr-platform");
  assert.equal(projection.source, "ledger");
  assert.equal(projection.runs.length, 1);
  assert.equal(projection.runs[0].ledgerOnly, true);
  assert.equal(projection.runs[0].jobs.length, 0);
  assert.equal(projection.runs[0].url, "https://github.com/example-org/adr-platform/actions/runs/789");
  assert.equal(core.historyProjection({ api_history_available: false, data_available: false, runs: [] }, "example-org/adr-platform"), null);
});

test("merges validated ledger records with server history without duplicating attempts", () => {
  const projection = core.historyProjection({
    api_history_available: true, data_available: true,
    workflow_runs: [{ id: 789, run_number: 12, run_attempt: 1, name: "Functional Analysis Demo",
      event: "workflow_dispatch", status: "completed", conclusion: "success",
      html_url: "https://github.com/example-org/adr-platform/actions/runs/789" }],
    runs: [
      { github_run_id: 789, run_attempt: 1, workflow_url: "https://github.com/example-org/adr-platform/actions/runs/789", status: "complete" },
      { github_run_id: 654, run_attempt: 2, workflow_url: "https://evil.invalid/actions/runs/654", status: "complete" },
      { github_run_id: 123, run_attempt: 1, workflow_url: "https://github.com/example-org/adr-platform/actions/runs/123", status: "complete" },
    ],
  }, "example-org/adr-platform");
  assert.equal(projection.source, "actions");
  assert.deepEqual(Array.from(projection.runs, run => `${run.id}:${run.attempt}`), ["789:1", "123:1"]);
  assert.equal(projection.runs[0].ledgerOnly, undefined);
  assert.equal(projection.runs[1].ledgerOnly, true);
});

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

test("puts every cited evidence item first and caps only supplemental evidence", () => {
  const evidence = Array.from({ length: 60 }, (_, index) => ({ id: `ev-${index}`, claim: `Claim ${index}` }));
  const selected = core.evidenceForFinding({ evidence_ids: ["ev-59", "ev-2"] }, evidence, 40);
  assert.deepEqual(Array.from(selected.slice(0, 2), item => item.item.id), ["ev-59", "ev-2"]);
  assert.equal(selected[0].isCited, true);
  assert.equal(selected[1].isCited, true);
  assert.equal(selected.length, 42);
  assert.equal(selected.slice(2).every(item => !item.isCited), true);
});

test("reports a missing cited evidence ID instead of returning a partial list", () => {
  assert.throws(() => core.evidenceForFinding({ evidence_ids: ["ev-missing"] }, [{ id: "ev-1" }]), /missing from the run snapshot/);
});

test("loads static Pages snapshots with same-origin credentials and rejects another origin", async () => {
  let captured;
  const data = await core.fetchSiteJson(async (url, options) => {
    captured = { url, options };
    return { ok: true, json: async () => ({ schema_version: "adr-demo-history-v1" }) };
  }, "data/real-runs.json", "https://internal.pages.github.io/project/demo/");
  assert.equal(data.schema_version, "adr-demo-history-v1");
  assert.equal(new URL(captured.url).origin, "https://internal.pages.github.io");
  assert.equal(captured.options.credentials, "same-origin");
  assert.equal(captured.options.mode, "same-origin");
  assert.equal(captured.options.redirect, "error");
  let requested = false;
  await assert.rejects(core.fetchSiteJson(async () => { requested = true; }, "https://evil.example/data.json", "https://internal.pages.github.io/"), /another origin/);
  assert.equal(requested, false);
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
