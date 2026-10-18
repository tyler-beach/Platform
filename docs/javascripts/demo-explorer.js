(function (root) {
  "use strict";

  const configuredRepository = root.document && root.document.querySelector('meta[name="adr-repository"]');
  const repositoryIdentity = configuredRepository && typeof configuredRepository.content === "string" && /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(configuredRepository.content)
    ? configuredRepository.content : "tyler-beach/Platform";
  const [OWNER, REPOSITORY] = repositoryIdentity.split("/");
  function safeRepository(value) {
    return typeof value === "string" && /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(value) ? value : `${OWNER}/${REPOSITORY}`;
  }
  function workflowDefinitions(repository) {
    const base = `https://github.com/${repository}`;
    return [
      { id: "poc-analysis.yml", title: "ADR Deviation PoC Analysis", launch: `${base}/actions/workflows/poc-analysis.yml` },
      { id: "poc-evaluation.yml", title: "ADR Deviation Labeled Evaluation", launch: `${base}/actions/workflows/poc-evaluation.yml` },
      { id: "functional-analysis-demo.yml", title: "Functional Analysis Demo", launch: `${base}/actions/workflows/functional-analysis-demo.yml` },
      { id: "pathfinder-issue-analyze.yml", title: "Pathfinder Issue Package Evaluation", launch: `${base}/actions/workflows/pathfinder-issue-analyze.yml` },
    ];
  }

  function issueAnalyzeLinks(repository) {
    const base = `https://github.com/${repository}`;
    return {
      issue: `${base}/issues/new?template=pathfinder-analyze.yml`,
      workflow: `${base}/actions/workflows/pathfinder-issue-analyze.yml`,
    };
  }
  const API = (repository) => `https://api.github.com/repos/${repository}`;
  const WORKFLOWS = workflowDefinitions(`${OWNER}/${REPOSITORY}`);
  const RUN_STATES = new Set(["queued", "in_progress", "completed", "waiting", "requested", "pending"]);
  const CONCLUSIONS = new Set(["success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"]);
  const STEP_STATES = new Set(["queued", "in_progress", "completed"]);
  const MAX_RUNS = 10;
  const GALLERY_MODES = ["code-diff", "technical-spec", "spec-vs-implementation"];
  const GALLERY_CASES = ["deviation", "aligned", "insufficient-evidence"];
  const GALLERY_OUTCOMES = { deviation: "supported_deviation", aligned: "no_deviation_found", "insufficient-evidence": "inconclusive" };
  const GALLERY_ROLES = new Set(["adr", "technical_spec", "implementation", "diff"]);
  let activeDemoCleanup = null;
  let demoGeneration = 0;
  function siteDataUrl(file) {
    const meta = root.document && root.document.querySelector('meta[name="adr-base-path"]');
    const basePath = meta && meta.content ? meta.content : "/";
    return new URL(`${basePath.replace(/\/$/, "")}/demo/data/${file}`, root.location.origin).href;
  }

  function plain(value, limit) {
    return typeof value === "string" ? value.slice(0, limit || 180) : "";
  }

  function positiveId(value) {
    return Number.isSafeInteger(value) && value > 0;
  }

  function safeRunUrl(value, id, repository = `${OWNER}/${REPOSITORY}`) {
    if (typeof value !== "string") return "";
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || url.hostname !== "github.com" || url.search || url.hash) return "";
      return url.pathname === `/${repository}/actions/runs/${id}` ? url.href : "";
    } catch (_) {
      return "";
    }
  }

  function safeJobUrl(value, repository = `${OWNER}/${REPOSITORY}`) {
    if (value === null || value === undefined || value === "") return true;
    if (typeof value !== "string") return false;
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || url.hostname !== "github.com") return false;
      const prefix = `/${repository}/`;
      return url.pathname.startsWith(prefix) && /^\/(?:actions\/runs\/\d+(?:\/job\/\d+)?|runs\/\d+(?:\/job\/\d+)?)$/.test(url.pathname.slice(prefix.length - 1));
    } catch (_) {
      return false;
    }
  }

  function normalizeRuns(rawRuns, repository = `${OWNER}/${REPOSITORY}`) {
    if (!Array.isArray(rawRuns)) return [];
    return rawRuns.filter((run) => run && positiveId(run.id) && positiveId(run.run_number) &&
      RUN_STATES.has(run.status) && safeRunUrl(run.html_url, run.id, repository))
      .slice(0, MAX_RUNS)
      .map((run) => ({
        id: run.id,
        number: run.run_number,
        attempt: positiveId(run.run_attempt) ? run.run_attempt : 1,
        name: plain(run.name || run.display_title || "Workflow run", 120),
        event: plain(run.event, 48),
        status: run.status,
        conclusion: CONCLUSIONS.has(run.conclusion) ? run.conclusion : "",
        branch: plain(run.head_branch, 80),
        sha: typeof run.head_sha === "string" && /^[a-f0-9]{7,40}$/i.test(run.head_sha) ? run.head_sha.slice(0, 12) : "",
        created: plain(run.created_at, 40),
        updated: plain(run.updated_at, 40),
        url: safeRunUrl(run.html_url, run.id, repository),
        workflowName: plain(run.workflow_name || run.name, 120),
        jobs: Array.isArray(run.jobs) ? normalizeJobs(run.jobs, repository) : undefined,
      }));
  }

  function normalizeLedgerRuns(rawRuns, repository = `${OWNER}/${REPOSITORY}`) {
    if (!Array.isArray(rawRuns)) return [];
    return rawRuns.slice(0, MAX_RUNS).flatMap((record) => {
      if (!record || !(typeof record.github_run_id === "number" || (typeof record.github_run_id === "string" && /^\d+$/.test(record.github_run_id)))) return [];
      const id = Number(record.github_run_id);
      const url = safeRunUrl(record.workflow_url, id, repository);
      if (!positiveId(id) || !url) return [];
      const status = ["complete", "failed", "cancelled", "model_response_rejected", "unknown"].includes(record.status) ? record.status : "unknown";
      const attempt = positiveId(record.run_attempt) ? record.run_attempt : 1;
      const comparison = plain(record.comparison, 80);
      const outcome = plain(record.outcome, 80);
      const functionalAnalysis = record.functional_analysis ? normalizeFunctionalAnalysis(record.functional_analysis) : null;
      if (record.functional_analysis && !functionalAnalysis) return [];
      if (outcome && !["supported_deviation", "no_deviation_found", "inconclusive"].includes(outcome)) return [];
      return [{
        id, number: id, attempt,
        name: functionalAnalysis ? `Functional Analysis · ${comparison || "analysis"} · ${outcome || functionalAnalysis.persistenceState}` : `PoC audit · ${comparison || "analysis"} · ${outcome || "inconclusive"}`,
        event: "PoC ledger record", status: "completed", conclusion: "",
        branch: "", sha: "", created: plain(record.started_at, 40), updated: plain(record.completed_at, 40),
        url, workflowName: "PoC analysis", jobs: [], ledgerOnly: true,
        ledgerStatus: status, ledgerOutcome: outcome, ledgerLanguage: plain(record.language, 40),
        ledgerProvider: plain(record.provider, 40), functionalAnalysis,
      }];
    });
  }

  function normalizeFunctionalAnalysis(record) {
    const states = new Set(["execution_only", "unreconciled", "validated_result"]);
    const outcomes = new Set(["", "supported_deviation", "no_deviation_found", "inconclusive"]);
    const types = new Set(["architectural_constraint", "syntax_call_site", "change_diff", "technical_requirement"]);
    if (!record || typeof record !== "object" || !states.has(record.persistence_state) ||
        !["completed"].includes(record.execution_status) || typeof record.execution_conclusion !== "string" ||
        !outcomes.has(record.domain_outcome) || record.confidence_status !== "unavailable" ||
        record.confidence_reason !== "The deterministic fixture oracle is not confidence; this workflow does not provide validated inputs for the evidence-strength algorithm." ||
        !Array.isArray(record.source_artifacts) || record.source_artifacts.length > 4 ||
        !Array.isArray(record.evidence_refs) || record.evidence_refs.length > 500 ||
        !Array.isArray(record.validation_checks) || record.validation_checks.length > 100) return null;
    const artifacts = new Map();
    for (const item of record.source_artifacts) {
      if (!item || typeof item.artifact_id !== "string" || !/^ART-[A-Z0-9-]{1,40}$/.test(item.artifact_id) ||
          artifacts.has(item.artifact_id) || !["adr", "implementation", "diff", "technical_spec"].includes(item.role) ||
          typeof item.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(item.sha256) ||
          typeof item.path !== "string" || !/^input\/[A-Za-z0-9_.-]{1,120}$/.test(item.path)) return null;
      artifacts.set(item.artifact_id, item);
    }
    const evidenceRefs = [];
    const evidenceIds = new Set();
    for (const item of record.evidence_refs) {
      const artifact = item && artifacts.get(item.artifact_id);
      if (!item || typeof item.evidence_id !== "string" || !/^EV-[A-Z0-9-]{1,48}$/.test(item.evidence_id) ||
          evidenceIds.has(item.evidence_id) || !artifact || item.source_sha256 !== artifact.sha256 ||
          item.evidence_type && !types.has(item.evidence_type) ||
          !Number.isSafeInteger(item.line_start) || item.line_start < 1 ||
          !Number.isSafeInteger(item.line_end) || item.line_end < item.line_start) return null;
      evidenceIds.add(item.evidence_id);
      evidenceRefs.push({ evidenceId: item.evidence_id, artifactId: item.artifact_id, sourceSha256: artifact.sha256,
        path: artifact.path, evidenceType: item.evidence_type || "", lineStart: item.line_start, lineEnd: item.line_end });
    }
    const checks = [];
    for (const item of record.validation_checks) {
      if (!item || typeof item.name !== "string" || !/^[A-Za-z0-9 ._:-]{1,120}$/.test(item.name) || typeof item.passed !== "boolean") return null;
      checks.push({ name: item.name, passed: item.passed });
    }
    if (record.persistence_state === "validated_result" &&
        (record.analysis_state !== "validated" || record.validation_status !== "passed" || !record.domain_outcome || checks.length === 0 || checks.some(item => !item.passed))) return null;
    if (record.persistence_state !== "validated_result" && (record.domain_outcome || record.validation_status !== "not_run" || evidenceRefs.length || artifacts.size)) return null;
    return {
      executionStatus: record.execution_status, executionConclusion: record.execution_conclusion,
      analysisState: plain(record.analysis_state, 40), persistenceState: record.persistence_state,
      persistenceReason: plain(record.persistence_reason, 180), domainOutcome: record.domain_outcome,
      validationStatus: plain(record.validation_status, 40), confidenceStatus: "unavailable",
      confidenceReason: record.confidence_reason, workflowSha: /^[a-f0-9]{40}$/i.test(record.workflow_sha || "") ? record.workflow_sha : "",
      comparisonContract: plain(record.comparison_contract, 80), sampleCase: plain(record.sample_case, 80),
      sourceArtifacts: Array.from(artifacts.values()).map(item => ({ artifactId: item.artifact_id, role: item.role, path: item.path, sha256: item.sha256 })),
      evidenceRefs, validationChecks: checks,
    };
  }

  function historyProjection(history, repository = `${OWNER}/${REPOSITORY}`) {
    if (!history || typeof history !== "object") return null;
    const ledgerRuns = normalizeLedgerRuns(history.runs, repository);
    if (history.api_history_available === true && Array.isArray(history.workflow_runs)) {
      const runs = normalizeRuns(history.workflow_runs, repository);
      const seen = new Set(runs.map((run) => `${run.id}:${run.attempt}`));
      ledgerRuns.forEach((run) => {
        const key = `${run.id}:${run.attempt}`;
        if (!seen.has(key)) { runs.push(run); seen.add(key); }
      });
      return { source: "actions", runs };
    }
    if (history.data_available === true) return { source: "ledger", runs: ledgerRuns };
    return null;
  }

  function normalizeScenarioGallery(value) {
    if (!value || value.schema_version !== "adr-synthetic-gallery-v1" ||
        value.source !== "checked-in synthetic Functional Analysis fixtures" ||
        typeof value.repository !== "string" || !/^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(value.repository) ||
        !Number.isSafeInteger(value.scenario_count) || value.scenario_count < 9 || value.scenario_count > 19 ||
        !Array.isArray(value.scenarios) || value.scenarios.length !== value.scenario_count ||
        !value.live_import || typeof value.live_import.enabled !== "boolean" ||
        !["eligible_runs", "imported", "rejected", "expired"].every(key => Number.isSafeInteger(value.live_import[key]) && value.live_import[key] >= 0 && value.live_import[key] <= 500)) {
      throw new Error("Synthetic scenario catalog is malformed or unsupported.");
    }
    const expected = new Set(GALLERY_MODES.flatMap(mode => GALLERY_CASES.map(sample => `${mode}--${sample}`)));
    const seen = new Set();
    const scenarios = value.scenarios.map(scenario => {
      const isCurated = scenario && expected.has(scenario.id) && scenario.record_type === "curated_fixture";
      const isLive = scenario && scenario.record_type === "workflow_run" && /^live-[1-9][0-9]*-[1-9][0-9]*$/.test(scenario.id || "");
      if (!scenario || typeof scenario !== "object" || (!isCurated && !isLive) || seen.has(scenario.id) ||
          !GALLERY_MODES.includes(scenario.comparison) || !GALLERY_CASES.includes(scenario.sample_case) ||
          (isCurated && scenario.id !== `${scenario.comparison}--${scenario.sample_case}`) ||
          scenario.outcome !== GALLERY_OUTCOMES[scenario.sample_case] || scenario.validation_status !== "passed" ||
          typeof scenario.rationale !== "string" || scenario.rationale.length > 1200 ||
          !Array.isArray(scenario.limitations) || scenario.limitations.length > 10 || scenario.limitations.some(item => typeof item !== "string" || item.length > 500) ||
          !Array.isArray(scenario.artifacts) || scenario.artifacts.length < 2 || scenario.artifacts.length > 4 ||
          !Array.isArray(scenario.evidence) || scenario.evidence.length < 1 || scenario.evidence.length > 100 ||
          !Array.isArray(scenario.stages) || scenario.stages.length !== 6 ||
          !Array.isArray(scenario.validation_checks) || scenario.validation_checks.length < 1 || scenario.validation_checks.length > 20 ||
          !Array.isArray(scenario.requirements) || scenario.requirements.length > 50 ||
          !Array.isArray(scenario.observations) || scenario.observations.length > 50) {
        throw new Error("Synthetic scenario record failed its shape or outcome checks.");
      }
      if (isLive && (!positiveId(scenario.run_id) || !positiveId(scenario.run_attempt) ||
          scenario.id !== `live-${scenario.run_id}-${scenario.run_attempt}` || !positiveId(scenario.workflow_id) ||
          typeof scenario.workflow_sha !== "string" || !/^[a-f0-9]{40}$/i.test(scenario.workflow_sha) ||
          typeof scenario.artifact_sha256 !== "string" || !/^sha256:[a-f0-9]{64}$/.test(scenario.artifact_sha256) ||
          typeof scenario.artifact_name !== "string" || scenario.artifact_name !== `functional-analysis-demo-${scenario.run_id}-${scenario.run_attempt}` ||
          !safeRunUrl(scenario.run_url, scenario.run_id, safeRepository(value.repository)))) {
        throw new Error("Live workflow artifact identity or provenance is malformed.");
      }
      seen.add(scenario.id);
      const roles = new Set();
      const artifactByRole = new Map();
      scenario.artifacts.forEach(item => {
        if (!item || !GALLERY_ROLES.has(item.role) || roles.has(item.role) ||
            typeof item.path !== "string" || !/^\.github\/demo\/fixtures\/[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*$/.test(item.path) ||
            typeof item.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(item.sha256) ||
            !Number.isSafeInteger(item.byte_length) || item.byte_length < 0 || item.byte_length > 32768 ||
            typeof item.text !== "string" || new TextEncoder().encode(item.text).length !== item.byte_length || item.text.length > 32768) {
          throw new Error("Synthetic scenario input failed its path, size, or digest metadata checks.");
        }
        roles.add(item.role);
        artifactByRole.set(item.role, item);
      });
      const wanted = scenario.comparison === "code-diff" ? ["adr", "implementation", "diff"]
        : scenario.comparison === "technical-spec" ? ["adr", "technical_spec"]
        : ["adr", "technical_spec", "implementation", "diff"];
      if (roles.size !== wanted.length || wanted.some(role => !roles.has(role))) throw new Error("Synthetic scenario inputs do not match the selected comparison.");
      const expectedPaths = { adr: ".github/demo/fixtures/adr/ADR-001.md" };
      if (scenario.comparison !== "technical-spec") {
        const extensions = { go: ".go", python: ".py", javascript: ".js", typescript: ".ts", java: ".java" };
        if (!extensions[scenario.language]) throw new Error("Synthetic scenario language is not supported.");
        const base = `.github/demo/fixtures/code-diff/${scenario.sample_case}/${scenario.language}`;
        expectedPaths.implementation = `${base}/handler${extensions[scenario.language]}`;
        expectedPaths.diff = `${base}/change.diff`;
      }
      if (scenario.comparison === "technical-spec") expectedPaths.technical_spec = `.github/demo/fixtures/technical-spec/${scenario.sample_case}.md`;
      if (scenario.comparison === "spec-vs-implementation") expectedPaths.technical_spec = ".github/demo/fixtures/technical-spec/aligned.md";
      if (scenario.artifacts.some(item => item.path !== expectedPaths[item.role])) throw new Error("Synthetic scenario source path does not match its selected fixture case.");
      const evidenceIds = new Set();
      scenario.evidence.forEach(item => {
        if (!item || typeof item.evidence_id !== "string" || !/^EV-[A-Z0-9-]{1,48}$/.test(item.evidence_id) ||
            evidenceIds.has(item.evidence_id) || !roles.has(item.role) || item.path !== artifactByRole.get(item.role).path ||
            !Number.isSafeInteger(item.line_start) || item.line_start < 1 ||
            !Number.isSafeInteger(item.line_end) || item.line_end < item.line_start ||
            typeof item.fact !== "string" || item.fact.length > 1000 || typeof item.excerpt !== "string" || item.excerpt.length > 2000) {
          throw new Error("Synthetic scenario evidence reference is malformed.");
        }
        evidenceIds.add(item.evidence_id);
      });
      scenario.stages.forEach(stage => {
        if (!stage || typeof stage.title !== "string" || typeof stage.summary !== "string" || stage.status !== "passed") {
          throw new Error("Synthetic scenario stage summary is malformed.");
        }
      });
      scenario.validation_checks.forEach(check => {
        if (!check || typeof check.name !== "string" || typeof check.passed !== "boolean" || !check.passed) {
          throw new Error("Synthetic scenario contains an invalid or failed validation check.");
        }
      });
      scenario.requirements.concat(scenario.observations).forEach(item => {
        if (!item || !Number.isSafeInteger(item.line) || item.line < 1 || typeof item.classification !== "string" ||
            typeof (item.text === undefined ? item.expression : item.text) !== "string") {
          throw new Error("Synthetic scenario analysis observation is malformed.");
        }
      });
      return scenario;
    });
    if (Array.from(expected).some(id => !seen.has(id)) || value.live_import.imported !== scenarios.filter(item => item.record_type === "workflow_run").length ||
        value.live_import.imported > 10 || value.live_import.eligible_runs > 10) {
      throw new Error("Synthetic scenario catalog does not contain the complete fixture matrix or consistent live artifact counts.");
    }
    return scenarios;
  }

  function galleryArtifactOrder(comparison, artifacts) {
    const roles = new Set(artifacts.map(item => item.role));
    const order = comparison === "spec-vs-implementation"
      ? ["technical_spec", "implementation", "adr", "diff"]
      : ["adr", "technical_spec", "implementation", "diff"];
    return order.filter(role => roles.has(role));
  }

  function galleryArtifactNode(doc, artifact) {
    const make = (tag, className, text) => {
      const node = doc.createElement(tag);
      if (className) node.className = className;
      node.textContent = String(text == null ? "" : text);
      return node;
    };
    const card = make("article", "demo-gallery-input");
    card.appendChild(make("span", "demo-eyebrow", artifact.role.replaceAll("_", " ")));
    card.appendChild(make("code", "demo-source-ref", artifact.path));
    card.appendChild(make("small", "demo-gallery-digest", `SHA-256 ${artifact.sha256} · ${artifact.byte_length} bytes`));
    card.appendChild(make("pre", "demo-excerpt demo-gallery-source", artifact.text));
    return card;
  }

  function normalizeJobs(rawJobs, repository = `${OWNER}/${REPOSITORY}`) {
    if (!Array.isArray(rawJobs)) return [];
    return rawJobs.filter((job) => job && positiveId(job.id) && typeof job.name === "string" &&
      RUN_STATES.has(job.status) && safeJobUrl(job.html_url, repository))
      .map((job) => ({
        id: job.id,
        name: plain(job.name, 120),
        status: job.status,
        conclusion: CONCLUSIONS.has(job.conclusion) ? job.conclusion : "",
        steps: (Array.isArray(job.steps) ? job.steps : [])
          .filter((step) => step && Number.isSafeInteger(step.number) && step.number > 0 &&
            typeof step.name === "string" && STEP_STATES.has(step.status))
          .map((step) => ({
            number: step.number, name: plain(step.name, 120), status: step.status,
            conclusion: CONCLUSIONS.has(step.conclusion) ? step.conclusion : "",
            started: plain(step.started_at, 40), completed: plain(step.completed_at, 40),
          }))
          .sort((left, right) => left.number - right.number),
      }));
  }

  function evidenceForFinding(finding, evidence, supplementalLimit = 40) {
    if (!Array.isArray(evidence)) throw new Error("Evidence list is malformed.");
    if (!Number.isSafeInteger(supplementalLimit) || supplementalLimit < 0) throw new Error("Evidence display limit is invalid.");
    const ids = finding && Array.isArray(finding.evidence_ids) ? finding.evidence_ids : [];
    if (ids.some((id) => typeof id !== "string" || !id)) throw new Error("Finding evidence references are malformed.");
    const byId = new Map();
    evidence.forEach((item) => {
      if (!item || typeof item.id !== "string" || !item.id || byId.has(item.id)) throw new Error("Evidence IDs are missing or ambiguous.");
      byId.set(item.id, item);
    });
    const cited = ids.map((id) => {
      const item = byId.get(id);
      if (!item) throw new Error(`Cited evidence ${id} is missing from the run snapshot.`);
      return { item, isCited: true };
    });
    const citedIds = new Set(ids);
    const additional = evidence.filter((item) => !citedIds.has(item.id)).slice(0, supplementalLimit)
      .map((item) => ({ item, isCited: false }));
    return cited.concat(additional);
  }

  async function requestJson(fetcher, url) {
    let response;
    try {
      response = await fetcher(url, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
        headers: { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" },
      });
    } catch (_) {
      throw new Error("GitHub Actions history is unavailable right now. The synthetic walkthrough still works.");
    }
    if (!response || !response.ok) {
      if (response && (response.status === 403 || response.status === 429)) {
        throw new Error("GitHub API rate limit reached. Try again later or open the Actions page.");
      }
      throw new Error(`GitHub Actions history request failed${response && response.status ? ` (${response.status})` : ""}. The synthetic walkthrough still works.`);
    }
    try {
      return await response.json();
    } catch (_) {
      throw new Error("GitHub returned unreadable workflow history. The synthetic walkthrough still works.");
    }
  }

  async function fetchSiteJson(fetcher, value, siteBase) {
    let origin;
    let url;
    try {
      origin = new URL(siteBase).origin;
      url = new URL(value, siteBase);
    } catch (_) {
      throw new Error("Pages snapshot URL is invalid.");
    }
    if (url.origin !== origin) throw new Error("Pages snapshot URL points to another origin.");
    let response;
    try {
      response = await fetcher(url.href, {
        method: "GET", mode: "same-origin", credentials: "same-origin", redirect: "error",
        referrerPolicy: "no-referrer", headers: { Accept: "application/json" },
      });
    } catch (_) {
      throw new Error("The Pages snapshot is unavailable. The synthetic walkthrough may still be used.");
    }
    if (!response || !response.ok) throw new Error(`Pages snapshot request failed${response && response.status ? ` (${response.status})` : ""}.`);
    try {
      return await response.json();
    } catch (_) {
      throw new Error("Pages returned unreadable snapshot data.");
    }
  }

  async function fetchWorkflowRuns(fetcher, workflow, repository = `${OWNER}/${REPOSITORY}`) {
    if (!WORKFLOWS.some((item) => item.id === workflow)) throw new Error("Workflow is not allowlisted.");
    repository = safeRepository(repository);
    const url = `${API(repository)}/actions/workflows/${encodeURIComponent(workflow)}/runs?per_page=${MAX_RUNS}`;
    const payload = await requestJson(fetcher, url);
    if (!payload || !Array.isArray(payload.workflow_runs)) throw new Error("GitHub returned malformed run history. The synthetic walkthrough still works.");
    return normalizeRuns(payload.workflow_runs, repository);
  }

  async function fetchRunJobs(fetcher, run, repository = `${OWNER}/${REPOSITORY}`) {
    if (!run || !positiveId(run.id) || !positiveId(run.attempt)) throw new Error("Run reference is invalid.");
    repository = safeRepository(repository);
    const url = `${API(repository)}/actions/runs/${run.id}/attempts/${run.attempt}/jobs?per_page=100`;
    const payload = await requestJson(fetcher, url);
    if (!payload || !Array.isArray(payload.jobs)) throw new Error("GitHub returned malformed job details.");
    return normalizeJobs(payload.jobs, repository);
  }

  function formatDate(value) {
    if (typeof value !== "string") return "Time unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
  }

  function statusText(item) {
    return item.conclusion || item.status || "unknown";
  }

  const core = { normalizeRuns, normalizeLedgerRuns, normalizeJobs, historyProjection, normalizeScenarioGallery, galleryArtifactOrder, galleryArtifactNode, evidenceForFinding, fetchSiteJson, fetchWorkflowRuns, fetchRunJobs, safeRunUrl, formatDate, statusText, workflows: WORKFLOWS };
  root.ADRDemoCore = core;

  function init() {
    if (!root.document) return;
    const mount = root.document.getElementById("demo-explorer");
    if (!mount || mount.dataset.demoInitialized === "true") return;
    mount.dataset.demoInitialized = "true";
    const generation = ++demoGeneration;
    const doc = root.document;
    const byId = (id) => doc.getElementById(id);
    const isCurrent = () => generation === demoGeneration && doc.getElementById("demo-explorer") === mount;
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value == null ? "" : String(value); };
    const el = (tag, className, text) => {
      const node = doc.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = String(text);
      return node;
    };
    function renderGallery(scenarios, selectedId) {
      const buttons = byId("demo-gallery-list");
      const inputs = byId("demo-gallery-inputs");
      const selected = scenarios.find(item => item.id === selectedId) || scenarios.find(item => item.id === "spec-vs-implementation--deviation") || scenarios[0];
      buttons.replaceChildren();
      scenarios.forEach(item => {
        const label = item.record_type === "workflow_run" ? `Actual run #${item.run_id} · attempt ${item.run_attempt}`
          : `${item.comparison.replaceAll("-", " ")} · ${item.sample_case.replaceAll("-", " ")}`;
        const button = el("button", "demo-gallery-choice", label);
        button.type = "button";
        button.setAttribute("aria-pressed", String(item.id === selected.id));
        button.addEventListener("click", () => renderGallery(scenarios, item.id));
        button.appendChild(el("span", "demo-gallery-choice__outcome", item.outcome.replaceAll("_", " ")));
        buttons.appendChild(button);
      });
      setText("demo-gallery-selected-title", selected.record_type === "workflow_run"
        ? `Actual workflow run #${selected.run_id} · attempt ${selected.run_attempt}`
        : `${selected.comparison.replaceAll("-", " ")} · ${selected.sample_case.replaceAll("-", " ")}`);
      setText("demo-gallery-selected-meta", selected.record_type === "workflow_run"
        ? `${selected.comparison} · ${selected.language} · updated ${formatDate(selected.updated_at)} · workflow SHA ${selected.workflow_sha.slice(0, 12)} · artifact ${selected.artifact_id} (${selected.artifact_name}) · ${selected.artifact_sha256}`
        : `${selected.language} · ${selected.artifacts.length} pinned synthetic inputs · deterministic mock`);
      setText("demo-gallery-selected-outcome", selected.outcome.replaceAll("_", " "));
      setText("demo-gallery-rationale", `${selected.rationale}${selected.limitations.length ? ` Limitations: ${selected.limitations.join(" ")}` : ""}`);
      const byRole = new Map(selected.artifacts.map(item => [item.role, item]));
      inputs.replaceChildren();
      galleryArtifactOrder(selected.comparison, selected.artifacts).forEach(role => inputs.appendChild(galleryArtifactNode(doc, byRole.get(role))));
      const runLink = byId("demo-gallery-run-link");
      runLink.replaceChildren();
      if (selected.record_type === "workflow_run") {
        const link = el("a", "md-button", `Open Functional Analysis run #${selected.run_id}`);
        link.href = selected.run_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        runLink.appendChild(link);
      }
      const stageList = byId("demo-gallery-stages");
      stageList.replaceChildren();
      selected.stages.forEach(stage => stageList.appendChild(el("li", "", `${stage.title} — ${stage.status}: ${stage.summary}`)));
      const requirementList = byId("demo-gallery-requirements");
      requirementList.replaceChildren();
      if (selected.requirements.length) selected.requirements.forEach(item => requirementList.appendChild(el("li", "", `Line ${item.line} · ${item.classification}: ${item.text}`)));
      else requirementList.appendChild(el("li", "demo-muted", "No technical-spec requirement was part of this comparison."));
      const observationList = byId("demo-gallery-observations");
      observationList.replaceChildren();
      if (selected.observations.length) selected.observations.forEach(item => observationList.appendChild(el("li", "", `Line ${item.line} · ${item.classification}: ${item.expression}`)));
      else observationList.appendChild(el("li", "demo-muted", "No code observation was part of this comparison."));
      const evidenceList = byId("demo-gallery-evidence");
      evidenceList.replaceChildren();
      selected.evidence.forEach(item => {
        const card = el("article", "demo-evidence-card");
        card.appendChild(el("span", "demo-eyebrow", `${item.evidence_id} · ${item.type.replaceAll("_", " ")}`));
        card.appendChild(el("h4", "", item.fact));
        card.appendChild(el("code", "demo-source-ref", `${item.path}:${item.line_start}-${item.line_end} · ${item.role}`));
        card.appendChild(el("pre", "demo-excerpt", item.excerpt));
        evidenceList.appendChild(card);
      });
      const checks = byId("demo-gallery-checks");
      checks.replaceChildren();
      selected.validation_checks.forEach(item => checks.appendChild(el("li", "", `PASS · ${item.name}`)));
    }

    async function loadGallery() {
      const status = byId("demo-gallery-status");
      try {
        const data = await fetchSiteJson(root.fetch.bind(root), siteDataUrl("scenario-gallery.json"), root.location.origin);
        if (!isCurrent()) return;
        const scenarios = normalizeScenarioGallery(data);
        renderGallery(scenarios);
        const live = scenarios.filter(item => item.record_type === "workflow_run").length;
        const rejected = data.live_import.rejected + data.live_import.expired;
        setText("demo-gallery-status", `Loaded 9 curated synthetic scenarios and ${live} validated Functional Analysis workflow artifacts.${rejected ? ` ${rejected} expired or rejected artifact(s) were excluded.` : ""} The live entries are recent workflow attempts, not an unbounded archive.`);
      } catch (error) {
        if (!isCurrent()) return;
        setText("demo-gallery-status", `${error.message} The separate synthetic walkthrough remains available.`);
        byId("demo-gallery-list").replaceChildren();
        byId("demo-gallery-inputs").replaceChildren();
      }
    }
    const addLink = (parent, href, text) => {
      const link = el("a", "demo-link", text);
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      parent.appendChild(link);
      return link;
    };

    let snapshot = null;
    let realHistory = null;
    let stageIndex = 0;
    let timer = 0;
    let selectedRun = null;
    let activeRepository = `${OWNER}/${REPOSITORY}`;
    const stagesNode = byId("demo-stages");
    const historyNode = byId("demo-run-list");
    const jobsNode = byId("demo-run-jobs");

    function renderStage(index) {
      if (!snapshot || !snapshot.stages.length) return;
      stageIndex = (index + snapshot.stages.length) % snapshot.stages.length;
      const stage = snapshot.stages[stageIndex];
      if (stagesNode) {
        stagesNode.querySelectorAll("[data-stage-index]").forEach((node) => {
          const active = Number(node.getAttribute("data-stage-index")) === stageIndex;
          node.classList.toggle("is-active", active);
          node.setAttribute("aria-current", active ? "step" : "false");
        });
      }
      setText("demo-stage-number", `${stageIndex + 1} / ${snapshot.stages.length}`);
      setText("demo-stage-title", stage.title);
      setText("demo-stage-description", stage.description);
      setText("demo-stage-status", `${stage.status} · ${stage.event_count} event${stage.event_count === 1 ? "" : "s"}`);
      const counts = byId("demo-stage-counts");
      if (counts) counts.textContent = Object.entries(stage.counts || {}).map(([key, value]) => `${key}: ${value}`).join(" · ") || "No count metadata for this stage.";
      setText("demo-stage-announcer", `Stage ${stageIndex + 1} of ${snapshot.stages.length}: ${stage.title}, ${stage.status}.`);
      byId("demo-previous").disabled = stageIndex === 0;
      byId("demo-next").disabled = stageIndex === snapshot.stages.length - 1;
    }

    function renderSnapshot() {
      if (!snapshot || snapshot.schema_version !== "adr-demo-run-v1") throw new Error("Walkthrough data has an unsupported version.");
      setText("demo-sample-label", snapshot.sample.label);
      setText("demo-sample-meta", `${snapshot.sample.comparison} · ${snapshot.sample.language} · mock provider`);
      setText("demo-final-outcome", snapshot.finding.outcome.replaceAll("_", " "));
      setText("demo-final-summary", snapshot.finding.summary);
      setText("demo-score", `${Math.round(snapshot.confidence.score)}/100`);
      setText("demo-score-band", snapshot.confidence.band);
      setText("demo-score-meaning", snapshot.confidence.interpretation);
      setText("demo-score-version", snapshot.confidence.algorithm_version);
      setText("demo-input-hash", snapshot.sample.input_sha256);

      const components = byId("demo-confidence-components");
      components.replaceChildren();
      snapshot.confidence.components.forEach((component) => {
        const row = el("article", "demo-component");
        row.appendChild(el("strong", "", component.dimension.replaceAll("_", " ")));
        row.appendChild(el("span", "", `${Math.round(component.score * 100)}% score · ${Math.round(component.weight * 100)}% weight`));
        row.appendChild(el("p", "", component.explanation));
        components.appendChild(row);
      });

      const evidence = byId("demo-evidence-list");
      renderEvidenceCards(evidence, snapshot.finding, snapshot.evidence);

      const observations = byId("demo-observation-list");
      observations.replaceChildren();
      snapshot.observations.forEach((item) => {
        const card = el("article", "demo-observation-card");
        card.appendChild(el("strong", "", item.predicate));
        card.appendChild(el("code", "demo-source-ref", item.source_path));
        card.appendChild(el("pre", "demo-excerpt", JSON.stringify({ value: item.value, resolution: item.resolution, locator: item.locator }, null, 2)));
        observations.appendChild(card);
      });

      const coverage = byId("demo-coverage-list");
      coverage.replaceChildren();
      snapshot.coverage.forEach((item) => {
        coverage.appendChild(el("li", "", `${item.source_type}: ${item.complete ? "complete" : "partial"} · ${item.emitted}/${item.inspected} observations · ${item.unresolved} unresolved · ${item.unsupported_count} unsupported`));
      });

      const stages = byId("demo-stages");
      stages.replaceChildren();
      snapshot.stages.forEach((stage, index) => {
        const button = el("button", "demo-stage-button", `${String(index + 1).padStart(2, "0")}  ${stage.title}`);
        button.type = "button";
        button.setAttribute("data-stage-index", String(index));
        button.addEventListener("click", () => { stopPlayback(); renderStage(index); });
        stages.appendChild(button);
      });
      renderStage(0);
    }

    function stopPlayback() {
      if (timer) root.clearInterval(timer);
      timer = 0;
      const play = byId("demo-play");
      if (play) { play.disabled = false; play.setAttribute("aria-pressed", "false"); }
      const pause = byId("demo-pause");
      if (pause) pause.disabled = true;
    }

    function renderRuns(runs) {
      historyNode.replaceChildren();
      if (!runs.length) {
        historyNode.appendChild(el("p", "demo-empty", "No runs were returned for these workflows yet."));
        return;
      }
      runs.sort((a, b) => {
        const left = Date.parse(a.updated || a.created);
        const right = Date.parse(b.updated || b.created);
        if (Number.isFinite(left) && Number.isFinite(right)) return right - left;
        return b.id - a.id || b.attempt - a.attempt;
      });
      runs.slice(0, MAX_RUNS).forEach((run) => {
        const card = el("article", "demo-run-card");
        const button = el("button", "demo-run-select", `#${run.number} · ${run.name}`);
        button.type = "button";
        button.addEventListener("click", () => showRunJobs(run));
        card.appendChild(button);
        const label = run.ledgerOnly ? run.ledgerStatus : statusText(run);
        card.appendChild(el("span", `demo-status demo-status--${label.replace(/[^a-z_]/g, "")}`, label.replaceAll("_", " ")));
        const metadata = run.functionalAnalysis
          ? `${run.functionalAnalysis.executionStatus} · ${run.functionalAnalysis.persistenceState} · outcome ${run.functionalAnalysis.domainOutcome || "not recorded"}`
          : run.ledgerOnly
          ? `${run.ledgerLanguage || "language unavailable"} · ${run.ledgerProvider || "provider unavailable"} · outcome ${run.ledgerOutcome || "inconclusive"}`
          : `${run.event || "workflow"} · ${run.branch || "branch unavailable"} · ${run.sha || "commit unavailable"}`;
        card.appendChild(el("p", "", metadata));
        card.appendChild(el("time", "", formatDate(run.updated || run.created)));
        addLink(card, run.url, "Open workflow run and artifacts");
        historyNode.appendChild(card);
      });
    }

    function renderEvidenceCards(container, finding, items) {
      container.replaceChildren();
      let selected;
      try {
        selected = evidenceForFinding(finding, items);
      } catch (error) {
        container.appendChild(el("p", "demo-warning", `Evidence integrity error: ${error.message}`));
        return;
      }
      selected.forEach(({ item, isCited }) => {
        const card = el("article", "demo-evidence-card");
        const kind = isCited ? "Finding citation" : "Additional run evidence";
        const redaction = item.redacted ? " · redacted" : "";
        card.appendChild(el("span", "demo-eyebrow", `${kind} · ${String(item.type || "evidence").replaceAll("_", " ")}${redaction}`));
        card.appendChild(el("h4", "", item.claim || "Evidence claim unavailable"));
        card.appendChild(el("code", "demo-source-ref", `Evidence ID ${item.id} · ${item.path || item.source_path || "source path unavailable"}:${item.line || "?"}`));
        card.appendChild(el("pre", "demo-excerpt", item.excerpt || JSON.stringify({ value: item.value, resolution: item.resolution, locator: item.locator }, null, 2) || "No excerpt"));
        const excerptDigest = item.displayed_excerpt_sha256 || item.excerpt_sha256 || item.recorded_excerpt_sha256 || "unavailable";
        card.appendChild(el("small", "", `Artifact SHA-256 ${item.source_sha256 || "unavailable"} · displayed excerpt SHA-256 ${excerptDigest}`));
        container.appendChild(card);
      });
    }

    async function showRunJobs(run) {
      selectedRun = run;
      renderRealRunRecord(run);
      if (run.ledgerOnly) {
        jobsNode.replaceChildren(el("p", "demo-empty", "This ledger-only record has no job or step metadata."));
        return;
      }
      jobsNode.replaceChildren(el("p", "demo-loading", `Loading jobs for run #${run.number}…`));
      try {
        const jobs = Array.isArray(run.jobs) ? normalizeJobs(run.jobs, activeRepository) : await fetchRunJobs(root.fetch.bind(root), run, activeRepository);
        jobsNode.replaceChildren();
        if (!jobs.length) jobsNode.appendChild(el("p", "demo-empty", "No job details were returned for this run."));
        jobs.forEach((job) => {
          const card = el("details", "demo-job-card");
          const summary = el("summary", "", `${job.name} · ${statusText(job).replaceAll("_", " ")}`);
          card.appendChild(summary);
          const list = el("ol", "demo-step-list");
          job.steps.forEach((step) => {
            const row = el("li", "", `${step.number}. ${step.name} — ${statusText(step).replaceAll("_", " ")}`);
            if (step.completed) row.appendChild(el("time", "", ` · ${formatDate(step.completed)}`));
            list.appendChild(row);
          });
          card.appendChild(list);
          jobsNode.appendChild(card);
        });
      } catch (error) {
        jobsNode.replaceChildren(el("p", "demo-warning", error.message));
      }
    }

    function renderRealRunRecord(run) {
      const panel = byId("demo-real-run-record");
      panel.replaceChildren();
      if (!realHistory || !Array.isArray(realHistory.runs)) return;
      const record = realHistory.runs.find((item) => Number(item.github_run_id) === run.id && Number(item.run_attempt || 1) === run.attempt) ||
        realHistory.runs.find((item) => Number(item.github_run_id) === run.id);
      if (!record) {
        panel.appendChild(el("p", "demo-empty", realHistory.data_available ? "No matching CSV run record was included in this Pages build." : "Detailed run records are disabled in this deployment; the synthetic walkthrough above shows the complete evidence trail."));
        return;
      }
      if (record.functional_analysis && run.functionalAnalysis) {
        renderFunctionalAnalysisRecord(panel, run, run.functionalAnalysis);
        return;
      }
      const details = el("details", "demo-real-record");
      details.open = true;
      details.appendChild(el("summary", "", `PoC audit record · ${record.comparison} · ${record.outcome.replaceAll("_", " ")}`));
      details.appendChild(el("p", "", `${record.source_path} · ${record.language} · ${record.provider} · input SHA-256 ${record.input_sha256}`));
      if (record.finding) {
        details.appendChild(el("h4", "", "Finding"));
        details.appendChild(el("p", "", record.finding.summary));
        details.appendChild(el("p", "demo-muted", record.finding.rationale));
      }
      if (record.confidence) {
        details.appendChild(el("h4", "", `Evidence-support score ${Math.round(record.confidence.score)}/100 · ${record.confidence.band}`));
        details.appendChild(el("p", "demo-muted", record.confidence.interpretation));
        const list = el("ul", "demo-real-components");
        record.confidence.components.forEach((item) => list.appendChild(el("li", "", `${item.dimension.replaceAll("_", " ")}: ${Math.round(item.score * 100)}% · weight ${Math.round(item.weight * 100)}% · ${item.explanation}`)));
        details.appendChild(list);
      }
      details.appendChild(el("h4", "", "Recorded PoC stages"));
      const stages = el("ol", "demo-real-stages");
      record.stages.forEach((stage) => stages.appendChild(el("li", "", `${stage.title} — ${stage.status}; ${stage.event_count} event(s)`)));
      details.appendChild(stages);
      details.appendChild(el("h4", "", "Evidence"));
      const evidence = el("div", "demo-evidence-grid");
      renderEvidenceCards(evidence, record.finding, record.evidence);
      details.appendChild(evidence);
      details.appendChild(el("h4", "", "Collection coverage"));
      const coverage = el("ul", "demo-coverage-list");
      record.coverage.forEach((item) => coverage.appendChild(el("li", "", `${item.source_type}: ${item.complete ? "complete" : "partial"} · ${item.emitted}/${item.inspected} observations · ${item.unresolved} unresolved · ${item.unsupported_count} unsupported`)));
      details.appendChild(coverage);
      const open = addLink(details, run.url, "Open original GitHub Actions run");
      open.className = "md-button";
      panel.appendChild(details);
    }

    function renderFunctionalAnalysisRecord(panel, run, record) {
      const details = el("details", "demo-real-record");
      details.open = true;
      details.appendChild(el("summary", "", `Functional Analysis audit · ${record.persistenceState.replaceAll("_", " ")}`));
      details.appendChild(el("p", "", `Execution: ${record.executionStatus} / ${record.executionConclusion} · analysis: ${record.analysisState} · persistence: ${record.persistenceState}`));
      details.appendChild(el("p", "", `Domain outcome: ${record.domainOutcome || "not recorded"} · validation: ${record.validationStatus}`));
      details.appendChild(el("h4", "", "Confidence"));
      details.appendChild(el("p", "demo-muted", `Unavailable — ${record.confidenceReason}`));
      if (record.persistenceReason) details.appendChild(el("p", "demo-muted", record.persistenceReason));
      if (record.workflowSha) details.appendChild(el("p", "", `Workflow source SHA: ${record.workflowSha}`));
      if (record.sourceArtifacts.length) {
        details.appendChild(el("h4", "", "Pinned source artifacts"));
        const sources = el("ul", "demo-real-stages");
        record.sourceArtifacts.forEach(item => sources.appendChild(el("li", "", `${item.artifactId} · ${item.role} · ${item.path} · SHA-256 ${item.sha256}`)));
        details.appendChild(sources);
      }
      if (record.evidenceRefs.length) {
        details.appendChild(el("h4", "", "Evidence references"));
        const refs = el("ul", "demo-real-stages");
        record.evidenceRefs.forEach(item => refs.appendChild(el("li", "", `${item.evidenceId} · ${item.evidenceType.replaceAll("_", " ")} · ${item.path}:${item.lineStart}-${item.lineEnd} · SHA-256 ${item.sourceSha256}`)));
        details.appendChild(refs);
      }
      if (record.validationChecks.length) {
        details.appendChild(el("h4", "", "Validation checks"));
        const checks = el("ul", "demo-real-stages");
        record.validationChecks.forEach(item => checks.appendChild(el("li", "", `${item.passed ? "PASS" : "FAIL"} · ${item.name}`)));
        details.appendChild(checks);
      }
      const open = addLink(details, run.url, "Open original GitHub Actions run");
      open.className = "md-button";
      panel.appendChild(details);
    }

    async function loadHistory() {
      setText("demo-history-status", "Loading recent Actions runs…");
      historyNode.replaceChildren();
      try {
        const data = await fetchSiteJson(root.fetch.bind(root), siteDataUrl("real-runs.json"), root.location.origin);
        if (!isCurrent()) return;
        if (data && data.schema_version === "adr-demo-history-v1") realHistory = data;
      } catch (_) {
        if (!isCurrent()) return;
        realHistory = null;
      }
      activeRepository = safeRepository(realHistory && realHistory.repository);
      const activeWorkflows = workflowDefinitions(activeRepository);
      const pasteLinks = issueAnalyzeLinks(activeRepository);
      byId("demo-open-analysis").href = activeWorkflows[0].launch;
      byId("demo-open-evaluation").href = activeWorkflows[1].launch;
      byId("demo-open-functional").href = activeWorkflows[2].launch;
      byId("demo-guide-analysis").href = activeWorkflows[0].launch;
      byId("demo-guide-evaluation").href = activeWorkflows[1].launch;
      byId("demo-guide-functional").href = activeWorkflows[2].launch;
      if (byId("demo-open-paste-analyze")) byId("demo-open-paste-analyze").href = pasteLinks.workflow;
      if (byId("demo-guide-paste-analyze")) byId("demo-guide-paste-analyze").href = pasteLinks.workflow;
      if (byId("demo-guide-paste-issue")) byId("demo-guide-paste-issue").href = pasteLinks.issue;
      if (byId("demo-open-paste-issue")) byId("demo-open-paste-issue").href = pasteLinks.issue;
      if (byId("demo-open-paste-workflow")) byId("demo-open-paste-workflow").href = pasteLinks.workflow;
      const projection = historyProjection(realHistory, activeRepository);
      if (projection) {
        const runs = projection.runs;
        setText("demo-history-status", projection.source === "actions"
          ? `Loaded ${runs.length} server-verified workflow and ledger records.`
          : `Loaded ${runs.length} ledger-backed audit records. Job and step statuses are not included.`);
        renderRuns(runs);
        if (selectedRun) renderRealRunRecord(selectedRun);
        return;
      }
      const workflows = activeWorkflows;
      const workflowIds = workflows.map((workflow) => workflow.id);
      try {
        const histories = await Promise.all(workflowIds.map((workflow) => fetchWorkflowRuns(root.fetch.bind(root), workflow, activeRepository)));
        if (!isCurrent()) return;
        const runs = histories.flat();
        setText("demo-history-status", `Loaded ${runs.length} recent Actions runs. Select a run to inspect job steps.`);
        renderRuns(runs);
        if (selectedRun) renderRealRunRecord(selectedRun);
      } catch (error) {
        if (!isCurrent()) return;
        setText("demo-history-status", error.message);
        historyNode.replaceChildren(el("p", "demo-warning", "Use these workflow links to view runs. The synthetic walkthrough above remains available."));
        workflows.forEach((workflow) => addLink(historyNode, workflow.launch, `Open ${workflow.title} in GitHub Actions`));
      }
    }

    byId("demo-previous").addEventListener("click", () => { stopPlayback(); renderStage(stageIndex - 1); });
    byId("demo-next").addEventListener("click", () => { stopPlayback(); renderStage(stageIndex + 1); });
    byId("demo-play").addEventListener("click", (event) => {
      if (!snapshot || timer) return;
      const play = event.currentTarget;
      play.disabled = true;
      play.setAttribute("aria-pressed", "true");
      byId("demo-pause").disabled = false;
      timer = root.setInterval(() => {
        if (stageIndex >= snapshot.stages.length - 1) { stopPlayback(); return; }
        renderStage(stageIndex + 1);
      }, 1800);
    });
    byId("demo-pause").addEventListener("click", stopPlayback);
    byId("demo-reload-history").addEventListener("click", loadHistory);
    loadGallery();
    const workflows = workflowDefinitions(`${OWNER}/${REPOSITORY}`);
    const pasteLinks = issueAnalyzeLinks(`${OWNER}/${REPOSITORY}`);
    byId("demo-open-analysis").href = workflows[0].launch;
    byId("demo-open-evaluation").href = workflows[1].launch;
    byId("demo-open-functional").href = workflows[2].launch;
    byId("demo-guide-analysis").href = workflows[0].launch;
    byId("demo-guide-evaluation").href = workflows[1].launch;
    byId("demo-guide-functional").href = workflows[2].launch;
    if (byId("demo-open-paste-analyze")) byId("demo-open-paste-analyze").href = pasteLinks.workflow;
    if (byId("demo-guide-paste-analyze")) byId("demo-guide-paste-analyze").href = pasteLinks.workflow;
    if (byId("demo-guide-paste-issue")) byId("demo-guide-paste-issue").href = pasteLinks.issue;
    if (byId("demo-open-paste-issue")) byId("demo-open-paste-issue").href = pasteLinks.issue;
    if (byId("demo-open-paste-workflow")) byId("demo-open-paste-workflow").href = pasteLinks.workflow;

    function renderPasteEval(data) {
      if (!byId("demo-paste-eval-status")) return;
      if (!data || data.schema_version !== "pathfinder-paste-eval-demo-v1") {
        setText("demo-paste-eval-status", "Paste-evaluation snapshot unavailable. Rebuild Pages demo data.");
        return;
      }
      const counts = data.counts || {};
      setText(
        "demo-paste-eval-status",
        `Fixture snapshot · aggregate ${data.aggregate_status} · ${data.observation_count} extracted observations · catalog ${data.catalog_size}. Live runs use GitHub Issues/Actions.`
      );
      const countList = byId("demo-paste-eval-counts");
      if (countList) {
        countList.replaceChildren();
        [
          `supported_deviation: ${counts.supported_deviation || 0}`,
          `no_deviation_found: ${counts.no_deviation_found || 0}`,
          `inconclusive: ${counts.inconclusive || 0}`,
          `not_applicable: ${counts.not_applicable || 0}`,
        ].forEach((line) => countList.appendChild(el("li", "", line)));
      }
      const predList = byId("demo-paste-eval-predicates");
      if (predList) {
        predList.replaceChildren();
        (data.extracted_observations || []).slice(0, 8).forEach((item) => {
          predList.appendChild(el("li", "", `${item.predicate} = ${JSON.stringify(item.value)}`));
        });
        if ((data.extracted_observations || []).length > 8) {
          predList.appendChild(el("li", "", `…and ${(data.extracted_observations.length - 8)} more (see Actions artifact on a live run)`));
        }
      }
    }

    activeDemoCleanup = () => { stopPlayback(); if (mount.dataset) delete mount.dataset.demoInitialized; };
    fetchSiteJson(root.fetch.bind(root), siteDataUrl("sample-run.json"), root.location.origin)
      .then((data) => { if (generation !== demoGeneration || doc.getElementById("demo-explorer") !== mount) return; snapshot = data; renderSnapshot(); })
      .catch((error) => {
        if (generation !== demoGeneration || doc.getElementById("demo-explorer") !== mount) return;
        setText("demo-sample-status", error.message + " Run the offline docs demo build to create it.");
        byId("demo-stage-title").textContent = "Walkthrough unavailable";
        byId("demo-stage-description").textContent = "The run history links remain available below.";
      });
    fetchSiteJson(root.fetch.bind(root), siteDataUrl("paste-eval-snapshot.json"), root.location.origin)
      .then((data) => { if (generation !== demoGeneration || doc.getElementById("demo-explorer") !== mount) return; renderPasteEval(data); })
      .catch((error) => {
        if (generation !== demoGeneration || doc.getElementById("demo-explorer") !== mount) return;
        setText("demo-paste-eval-status", `${error.message} Rebuild Pages to regenerate the paste-eval snapshot.`);
      });
    loadHistory();
  }

  root.ADRDemoLifecycle = { init, destroy() { demoGeneration += 1; if (activeDemoCleanup) activeDemoCleanup(); activeDemoCleanup = null; } };
  if (root.document) {
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
  }
})(globalThis);
