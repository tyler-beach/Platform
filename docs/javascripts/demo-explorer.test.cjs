const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "demo-explorer.js"), "utf8");
const context = { URL, Date, Math, Array, Object, Number, String, Promise, TextEncoder, console, document: undefined };
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "demo-explorer.js" });
const core = context.ADRDemoCore;

test("offers the Functional Analysis Demo workflow alongside the audit workflows", () => {
  assert.ok(core.workflows.some(workflow => workflow.id === "functional-analysis-demo.yml"));
});

test("offers Pathfinder issue package evaluation workflow for catalog runs", () => {
  assert.ok(core.workflows.some(workflow => workflow.id === "pathfinder-issue-analyze.yml"));
  assert.match(source, /paste-eval-snapshot\.json/);
  assert.match(source, /pathfinder-analyze\.yml/);
});

test("builds and validates Pathfinder analyze issue bodies for GitHub submission", () => {
  const error = core.validatePastePrepare({ techSpec: "", code: "", attested: false });
  assert.match(error, /attestation/i);
  const missing = core.validatePastePrepare({ techSpec: "", code: "", pullRequest: "", attested: true });
  assert.match(missing, /tech spec|sample code|pull request/i);
  const prOnly = core.validatePastePrepare({ techSpec: "", code: "", pullRequest: "#57", attested: true });
  assert.equal(prOnly, "");
  const body = core.buildPasteIssueBody({
    techSpec: "Sessions expire after 12 minutes.",
    code: "package main",
    domains: "identity",
    pullRequest: "https://github.com/tyler-beach/Platform/pull/57",
    attested: true,
  });
  assert.match(body, /\[X\]/);
  assert.match(body, /### Tech spec \(markdown\)/);
  assert.match(body, /### Catalog pack/);
  assert.match(body, /Real prototype pack/);
  assert.match(body, /### Same-repo pull request \(optional\)/);
  assert.match(body, /Sessions expire after 12 minutes/);
  assert.match(body, /pull\/57/);
  const shortPlan = core.githubPasteIssuePlan("tyler-beach/Platform", {
    title: "[Pathfinder analyze] demo",
    body: "short",
  });
  assert.equal(shortPlan.mode, "url_body");
  assert.equal(shortPlan.copyRequired, false);
  const longPlan = core.githubPasteIssuePlan("tyler-beach/Platform", {
    title: "[Pathfinder analyze] demo",
    body: "x".repeat(6000),
  });
  assert.equal(longPlan.mode, "copy_then_template");
  assert.equal(longPlan.copyRequired, true);
});

test("uses the configured private clone identity for workflow links", () => {
  const configured = { content: "example-org/adr-platform" };
  const document = { readyState: "loading", querySelector: () => configured, addEventListener() {} };
  const isolated = { URL, Date, Math, Array, Object, Number, String, Promise, TextEncoder, console, document };
  isolated.globalThis = isolated;
  vm.runInNewContext(source, isolated, { filename: "demo-explorer.js" });
  assert.equal(isolated.ADRDemoCore.workflows[0].launch, "https://github.com/example-org/adr-platform/actions/workflows/poc-analysis.yml");
  configured.content = "javascript:alert(1)";
  const unsafe = { ...isolated, document: { ...document, querySelector: () => configured } };
  unsafe.globalThis = unsafe;
  vm.runInNewContext(source, unsafe, { filename: "demo-explorer.js" });
  assert.equal(unsafe.ADRDemoCore.workflows[0].launch, "https://github.com/tyler-beach/Platform/actions/workflows/poc-analysis.yml");
});

function syntheticGallery() {
  const modes = ["code-diff", "technical-spec", "spec-vs-implementation"];
  const cases = ["deviation", "aligned", "insufficient-evidence"];
  const outcomes = { deviation: "supported_deviation", aligned: "no_deviation_found", "insufficient-evidence": "inconclusive" };
  const roles = { "code-diff": ["adr", "implementation", "diff"], "technical-spec": ["adr", "technical_spec"], "spec-vs-implementation": ["adr", "technical_spec", "implementation", "diff"] };
  return { schema_version: "adr-synthetic-gallery-v1", source: "checked-in synthetic Functional Analysis fixtures", repository: "tyler-beach/Platform", scenario_count: 9,
    live_import: { enabled: false, eligible_runs: 0, imported: 0, rejected: 0, expired: 0 },
    scenarios: modes.flatMap(comparison => cases.map(sample_case => {
      const language = comparison === "technical-spec" ? "not_applicable" : "go";
      const base = `.github/demo/fixtures/code-diff/${sample_case}/go`;
      const paths = { adr: ".github/demo/fixtures/adr/ADR-001.md", technical_spec: comparison === "spec-vs-implementation" ? ".github/demo/fixtures/technical-spec/aligned.md" : `.github/demo/fixtures/technical-spec/${sample_case}.md`, implementation: `${base}/handler.go`, diff: `${base}/change.diff` };
      return {
      id: `${comparison}--${sample_case}`, comparison, sample_case, language, outcome: outcomes[sample_case], validation_status: "passed", rationale: "Fixture result.", limitations: [],
      record_type: "curated_fixture",
      artifacts: roles[comparison].map(role => ({ role, path: paths[role], sha256: "a".repeat(64), byte_length: 4, text: "safe" })),
      evidence: [{ evidence_id: "EV-ADR-001", role: roles[comparison][0], path: paths[roles[comparison][0]], type: "architectural_constraint", line_start: 1, line_end: 1, fact: "Bounded fact", excerpt: "safe" }],
      requirements: [], observations: [],
      stages: Array.from({ length: 6 }, (_, index) => ({ title: `Stage ${index}`, status: "passed", summary: "Complete" })),
      validation_checks: [{ name: "Fixture validation passed", passed: true }],
    }; })) };
}

test("accepts the complete nine-case synthetic scenario gallery", () => {
  const scenarios = core.normalizeScenarioGallery(syntheticGallery());
  assert.equal(scenarios.length, 9);
  assert.ok(scenarios.some(item => item.id === "spec-vs-implementation--deviation"));
  assert.deepEqual(Array.from(core.galleryArtifactOrder("spec-vs-implementation", scenarios[8].artifacts)), ["technical_spec", "implementation", "adr", "diff"]);
});

test("accepts a provenance-bound live workflow attempt alongside curated scenarios", () => {
  const gallery = syntheticGallery();
  gallery.repository = "example-org/adr-platform";
  const live = structuredClone(gallery.scenarios[0]);
  Object.assign(live, { id: "live-789-2", record_type: "workflow_run", run_id: 789, run_attempt: 2,
    workflow_id: 456, workflow_sha: "b".repeat(40), artifact_name: "functional-analysis-demo-789-2",
    artifact_sha256: `sha256:${"c".repeat(64)}`, run_url: "https://github.com/example-org/adr-platform/actions/runs/789" });
  gallery.scenarios.push(live);
  gallery.scenario_count = 10;
  gallery.live_import = { enabled: true, eligible_runs: 1, imported: 1, rejected: 0, expired: 0 };
  assert.equal(core.normalizeScenarioGallery(gallery).length, 10);
  live.run_url = "https://evil.example/actions/runs/789";
  assert.throws(() => core.normalizeScenarioGallery(gallery), /identity or provenance/);
});

test("rejects incomplete scenarios and artifact paths outside synthetic fixtures", () => {
  const missing = syntheticGallery();
  missing.scenarios.pop();
  assert.throws(() => core.normalizeScenarioGallery(missing), /malformed or unsupported/);
  const unsafe = syntheticGallery();
  unsafe.scenarios[0].artifacts[0].path = "../../secrets.txt";
  assert.throws(() => core.normalizeScenarioGallery(unsafe), /path, size, or digest/);
});

test("renders source contents as text rather than HTML", () => {
  const document = { createElement: tag => ({ tag, children: [], appendChild(child) { this.children.push(child); } }) };
  // Split the payload so static scanners do not treat this security regression fixture as an XSS sink.
  const hostileMarkup = ["<", "script", ">alert(1)</", "script", ">"].join("");
  const node = core.galleryArtifactNode(document, {
    role: "implementation",
    path: "fixture.go",
    sha256: "a".repeat(64),
    byte_length: hostileMarkup.length,
    text: hostileMarkup,
  });
  const preNode = node.children.find(child => child.tag === "pre");
  assert.equal(preNode.textContent, hostileMarkup);
  assert.equal(preNode.children.length, 0);
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

test("normalizes functional analysis records without fabricating confidence or domain outcomes", () => {
  const projection = core.historyProjection({
    api_history_available: false, data_available: true, workflow_runs: [],
    runs: [{ github_run_id: 789, run_attempt: 2,
      workflow_url: "https://github.com/example-org/adr-platform/actions/runs/789",
      comparison: "code-diff", language: "go", status: "complete", outcome: "supported_deviation",
      functional_analysis: { execution_status: "completed", execution_conclusion: "success",
        analysis_state: "validated", persistence_state: "validated_result", validation_status: "passed",
        domain_outcome: "supported_deviation", confidence_status: "unavailable",
        confidence_reason: "The deterministic fixture oracle is not confidence; this workflow does not provide validated inputs for the evidence-strength algorithm.", source_artifacts: [{ artifact_id: "ART-1", role: "implementation", sha256: "a".repeat(64), path: "input/main.go" }],
        evidence_refs: [{ evidence_id: "EV-1", artifact_id: "ART-1", source_sha256: "a".repeat(64), line_start: 3, line_end: 3 }],
        validation_checks: [{ name: "source hashes valid", passed: true }] } }],
  }, "example-org/adr-platform");
  assert.equal(projection.runs.length, 1);
  assert.equal(projection.runs[0].functionalAnalysis.confidenceStatus, "unavailable");
  assert.equal(projection.runs[0].functionalAnalysis.domainOutcome, "supported_deviation");
  assert.equal(projection.runs[0].functionalAnalysis.evidenceRefs[0].evidenceId, "EV-1");
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
