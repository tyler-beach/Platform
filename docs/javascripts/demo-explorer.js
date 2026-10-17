(function (root) {
  "use strict";

  const OWNER = "tyler-beach";
  const REPOSITORY = "Platform";
  function safeRepository(value) {
    return typeof value === "string" && /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(value) ? value : `${OWNER}/${REPOSITORY}`;
  }
  function workflowDefinitions(repository) {
    const base = `https://github.com/${repository}`;
    return [
      { id: "poc-analysis.yml", title: "ADR Deviation PoC Analysis", launch: `${base}/actions/workflows/poc-analysis.yml` },
      { id: "poc-evaluation.yml", title: "ADR Deviation Labeled Evaluation", launch: `${base}/actions/workflows/poc-evaluation.yml` },
    ];
  }
  const API = (repository) => `https://api.github.com/repos/${repository}`;
  const WORKFLOWS = workflowDefinitions(`${OWNER}/${REPOSITORY}`);
  const RUN_STATES = new Set(["queued", "in_progress", "completed", "waiting", "requested", "pending"]);
  const CONCLUSIONS = new Set(["success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"]);
  const STEP_STATES = new Set(["queued", "in_progress", "completed"]);
  const MAX_RUNS = 10;

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

  const core = { normalizeRuns, normalizeJobs, fetchWorkflowRuns, fetchRunJobs, safeRunUrl, formatDate, statusText, workflows: WORKFLOWS };
  root.ADRDemoCore = core;

  function init() {
    if (!root.document || !root.document.getElementById("demo-explorer")) return;
    const doc = root.document;
    const byId = (id) => doc.getElementById(id);
    const setText = (id, value) => { const node = byId(id); if (node) node.textContent = value == null ? "" : String(value); };
    const el = (tag, className, text) => {
      const node = doc.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = String(text);
      return node;
    };
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
      evidence.replaceChildren();
      snapshot.evidence.forEach((item) => {
        const card = el("article", "demo-evidence-card");
        card.appendChild(el("span", "demo-eyebrow", item.type.replaceAll("_", " ")));
        card.appendChild(el("h4", "", item.claim));
        card.appendChild(el("code", "demo-source-ref", `${item.path}:${item.line || "?"}`));
        card.appendChild(el("pre", "demo-excerpt", item.excerpt || "No excerpt"));
        card.appendChild(el("small", "", `Source SHA-256 ${item.source_sha256} · excerpt SHA-256 ${item.excerpt_sha256}`));
        evidence.appendChild(card);
      });

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
      runs.sort((a, b) => Date.parse(b.updated || b.created) - Date.parse(a.updated || a.created));
      runs.slice(0, MAX_RUNS).forEach((run) => {
        const card = el("article", "demo-run-card");
        const button = el("button", "demo-run-select", `#${run.number} · ${run.name}`);
        button.type = "button";
        button.addEventListener("click", () => showRunJobs(run));
        card.appendChild(button);
        card.appendChild(el("span", `demo-status demo-status--${statusText(run).replace(/[^a-z_]/g, "")}`, statusText(run).replaceAll("_", " ")));
        card.appendChild(el("p", "", `${run.event || "workflow"} · ${run.branch || "branch unavailable"} · ${run.sha || "commit unavailable"}`));
        card.appendChild(el("time", "", formatDate(run.updated || run.created)));
        addLink(card, run.url, "Open workflow run and artifacts");
        historyNode.appendChild(card);
      });
    }

    async function showRunJobs(run) {
      selectedRun = run;
      renderRealRunRecord(run);
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
      record.evidence.slice(0, 40).forEach((item) => {
        const card = el("article", "demo-evidence-card");
        card.appendChild(el("span", "demo-eyebrow", `${item.type.replaceAll("_", " ")}${item.redacted ? " · redacted" : ""}`));
        card.appendChild(el("h4", "", item.claim));
        card.appendChild(el("code", "demo-source-ref", `${item.path}:${item.line || "?"}`));
        card.appendChild(el("pre", "demo-excerpt", item.excerpt || "No excerpt"));
        card.appendChild(el("small", "", `Artifact SHA-256 ${item.source_sha256} · displayed excerpt SHA-256 ${item.displayed_excerpt_sha256 || item.recorded_excerpt_sha256}`));
        evidence.appendChild(card);
      });
      details.appendChild(evidence);
      details.appendChild(el("h4", "", "Collection coverage"));
      const coverage = el("ul", "demo-coverage-list");
      record.coverage.forEach((item) => coverage.appendChild(el("li", "", `${item.source_type}: ${item.complete ? "complete" : "partial"} · ${item.emitted}/${item.inspected} observations · ${item.unresolved} unresolved · ${item.unsupported_count} unsupported`)));
      details.appendChild(coverage);
      const open = addLink(details, run.url, "Open original GitHub Actions run");
      open.className = "md-button";
      panel.appendChild(details);
    }

    async function loadHistory() {
      setText("demo-history-status", "Loading recent Actions runs…");
      historyNode.replaceChildren();
      try {
        const response = await root.fetch(new URL("data/real-runs.json", doc.baseURI), { credentials: "omit", referrerPolicy: "no-referrer" });
        if (response.ok) {
          const data = await response.json();
          if (data && data.schema_version === "adr-demo-history-v1") realHistory = data;
        }
      } catch (_) {
        realHistory = null;
      }
      activeRepository = safeRepository(realHistory && realHistory.repository);
      const activeWorkflows = workflowDefinitions(activeRepository);
      byId("demo-open-analysis").href = activeWorkflows[0].launch;
      byId("demo-open-evaluation").href = activeWorkflows[1].launch;
      byId("demo-guide-analysis").href = activeWorkflows[0].launch;
      byId("demo-guide-evaluation").href = activeWorkflows[1].launch;
      if (realHistory && realHistory.api_history_available && Array.isArray(realHistory.workflow_runs)) {
        const runs = normalizeRuns(realHistory.workflow_runs, activeRepository);
        setText("demo-history-status", `Loaded ${runs.length} server-verified workflow runs. Detailed audit rows are included only for the internal Pages deployment.`);
        renderRuns(runs);
        if (selectedRun) renderRealRunRecord(selectedRun);
        return;
      }
      const workflows = activeWorkflows;
      const workflowIds = workflows.map((workflow) => workflow.id);
      try {
        const histories = await Promise.all(workflowIds.map((workflow) => fetchWorkflowRuns(root.fetch.bind(root), workflow, activeRepository)));
        const runs = histories.flat();
        setText("demo-history-status", `Loaded ${runs.length} recent Actions runs. Select a run to inspect job steps.`);
        renderRuns(runs);
        if (selectedRun) renderRealRunRecord(selectedRun);
      } catch (error) {
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
    const workflows = workflowDefinitions(`${OWNER}/${REPOSITORY}`);
    byId("demo-open-analysis").href = workflows[0].launch;
    byId("demo-open-evaluation").href = workflows[1].launch;
    byId("demo-guide-analysis").href = workflows[0].launch;
    byId("demo-guide-evaluation").href = workflows[1].launch;

    root.fetch(new URL("data/sample-run.json", doc.baseURI), { credentials: "omit", referrerPolicy: "no-referrer" })
      .then((response) => { if (!response.ok) throw new Error("The fixture walkthrough could not be loaded."); return response.json(); })
      .then((data) => { snapshot = data; renderSnapshot(); })
      .catch((error) => {
        setText("demo-sample-status", error.message + " Run the offline docs demo build to create it.");
        byId("demo-stage-title").textContent = "Walkthrough unavailable";
        byId("demo-stage-description").textContent = "The run history links remain available below.";
      });
    loadHistory();
  }

  if (root.document) {
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
  }
})(globalThis);
