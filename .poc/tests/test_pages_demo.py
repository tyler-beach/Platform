from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "demo"))

from actions_history import collect_history
from export_site_snapshot import build_history_snapshot, build_snapshot, export_snapshot
from pages_visibility import actions_history_export_enabled, real_data_export_enabled
from prepare_site import prepare_site


class PagesSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pages-demo-", dir=ROOT / ".poc")
        self.base = Path(self.temp.name)
        self.fixture = ROOT / ".poc/fixtures/go"
        self.db = self.base / "db"
        self.out = self.base / "runs"
        self.run_dir = self.out / "pages-fixture-walkthrough"
        command = [
            sys.executable, str(ROOT / ".poc/run.py"), "--source", str(self.fixture), "--language", "go",
            "--comparison", "spec-vs-implementation", "--provider", "mock", "--run-id", "pages-fixture-walkthrough",
            "--root-function", "Submit", "--db-dir", str(self.db), "--out-dir", str(self.out),
            "--adr-path", str(self.fixture / "ADR-001.md"), "--spec-path", str(self.fixture / "technical-spec.md"),
            "--diff-path", str(self.fixture / "change.diff"),
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            self.fail("Fixture mock analysis failed: " + result.stderr)

    def tearDown(self):
        self.temp.cleanup()

    def _rewrite_table(self, name, update):
        path = self.db / f"{name}.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames
            rows = list(reader)
        update(rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    def test_snapshot_contains_explorable_allowlisted_demo_outputs(self):
        snapshot = build_snapshot(self.db, self.run_dir, self.fixture)
        self.assertEqual(snapshot["schema_version"], "adr-demo-run-v1")
        self.assertEqual(snapshot["sample"]["provider"], "mock")
        self.assertTrue(snapshot["sample"]["synthetic"])
        self.assertGreaterEqual(len(snapshot["stages"]), 6)
        self.assertTrue(snapshot["evidence"])
        self.assertTrue(snapshot["confidence"]["components"])
        self.assertIn("not a calibrated probability", snapshot["confidence"]["interpretation"].lower())
        cited_ids = snapshot["finding"]["evidence_ids"]
        self.assertTrue(cited_ids)
        self.assertTrue(set(cited_ids).issubset({item["id"] for item in snapshot["evidence"]}))
        serialized = json.dumps(snapshot).lower()
        for forbidden in ("anthropic_api_key", "prompt_sha256", "model_candidate", "raw_source", "private key"):
            self.assertNotIn(forbidden, serialized)

    def test_exporter_fails_closed_when_artifact_is_outside_fixture_root(self):
        artifacts = self.db / "artifacts.csv"
        contents = artifacts.read_text(encoding="utf-8")
        artifacts.write_text(contents.replace(".poc/fixtures/go/", "../../private-project/", 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside approved synthetic fixture"):
            build_snapshot(self.db, self.run_dir, self.fixture)

    def test_export_writes_versioned_json_and_rejects_output_outside_site_data(self):
        site_data = self.base / "site/demo/data"
        destination = export_snapshot(self.db, self.run_dir, self.fixture, site_data / "sample-run.json")
        self.assertTrue(destination.is_file())
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["schema_version"], "adr-demo-run-v1")
        with self.assertRaisesRegex(ValueError, "must be under site demo data"):
            export_snapshot(self.db, self.run_dir, self.fixture, self.base / "public.json")

    def test_demo_page_explains_workflows_scores_privacy_and_reduced_motion(self):
        page = (ROOT / "docs/demo/index.md").read_text(encoding="utf-8")
        javascript = (ROOT / "docs/javascripts/demo-explorer.js").read_text(encoding="utf-8")
        styles = (ROOT / "docs/stylesheets/extra.css").read_text(encoding="utf-8")
        config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("poc-analysis.yml", javascript)
        self.assertIn("poc-evaluation.yml", javascript)
        self.assertIn("not a calibrated probability", page.lower())
        self.assertIn("synthetic", page.lower())
        for control in ("demo-previous", "demo-next", "demo-play", "demo-pause", "demo-reload-history"):
            self.assertIn(f'id="{control}"', page)
        for link in ("demo-open-analysis", "demo-open-evaluation", "demo-open-functional", "demo-guide-analysis", "demo-guide-evaluation", "demo-guide-functional"):
            self.assertIn(f'id="{link}"', page)
        self.assertNotIn("https://github.com/tyler-beach/Platform/actions/workflows/", page)
        self.assertIn("aria-live", page)
        self.assertIn("prefers-reduced-motion: reduce", styles)
        self.assertIn("demo/index.md", config)
        self.assertIn('textContent', javascript)
        self.assertIn("Finding citation", javascript)
        self.assertIn("Additional run evidence", javascript)
        self.assertIn("evidenceForFinding", javascript)
        self.assertIn('fetchSiteJson(root.fetch.bind(root), "data/real-runs.json", root.location.origin)', javascript)
        self.assertIn('fetchSiteJson(root.fetch.bind(root), "data/sample-run.json", root.location.origin)', javascript)
        self.assertIn('credentials: "same-origin"', javascript)
        self.assertNotIn(".innerHTML", javascript)
        self.assertNotIn(".insertAdjacentHTML", javascript)
        self.assertNotIn("autoplay", page.lower())

    def test_docs_workflow_rebuilds_fixture_and_validates_site_snapshot(self):
        workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
        for required in (
            "actions/setup-go@v5", "node --test docs/javascripts/demo-explorer.test.cjs",
            "python .poc/run.py", "--provider mock", "export_site_snapshot.py",
            "site/demo/data/sample-run.json", "mkdocs build --strict", "actions/deploy-pages@v4",
        ):
            self.assertIn(required, workflow)
        self.assertIn("if: github.event_name != 'pull_request'", workflow)
        self.assertIn("HISTORY_OPT_IN: ${{ vars.PAGES_ACTIONS_HISTORY_ENABLED }}", workflow)
        self.assertIn("REAL_DATA_OPT_IN: ${{ vars.PAGES_REAL_RUN_DATA_ENABLED }}", workflow)
        self.assertIn('workflows: ["ADR Deviation PoC Analysis", "ADR Deviation Labeled Evaluation", "Functional Analysis Demo"]', workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("github.event.workflow_run.event != 'pull_request'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("Resolve this repository's Pages and source URLs", workflow)
        self.assertIn("prepare_site.py", workflow)
        self.assertIn("PAGES_REAL_RUN_DATA_ENABLED", workflow)
        self.assertIn("/pages", workflow)
        self.assertIn('owner.get("type", "") if isinstance(owner, dict) else ""', workflow)
        self.assertIn("ADR_REPO_URL", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        self.assertIn("ADR_REPO_NAME", workflow)
        self.assertIn('functional-analysis-demo.yml', workflow)
        self.assertIn('id="demo-open-functional"', (ROOT / "docs/demo/index.md").read_text(encoding="utf-8"))

    def test_docs_workflow_has_independent_history_and_ledger_gates(self):
        workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
        history_gate = workflow.index('if [[ "$HISTORY_OPT_IN" == "true" ]]')
        ledger_gate = workflow.index('if [[ "$REAL_DATA_OPT_IN" == "true" ]]; then')
        history_api = workflow.index("python .poc/demo/actions_history.py")
        ledger_clone = workflow.index('gh repo clone "$GITHUB_REPOSITORY"')
        self.assertLess(history_gate, history_api)
        self.assertLess(ledger_gate, ledger_clone)
        history_only_block = workflow.split('if [[ "$HISTORY_OPT_IN" == "true" ]]; then', 1)[1].split("else", 1)[0]
        ledger_only_block = workflow.split('if [[ "$REAL_DATA_OPT_IN" == "true" ]]; then', 1)[1].split("else", 1)[0]
        self.assertIn("python .poc/demo/actions_history.py", history_only_block)
        self.assertNotIn('gh repo clone "$GITHUB_REPOSITORY"', history_only_block)
        self.assertIn('gh repo clone "$GITHUB_REPOSITORY"', ledger_only_block)
        self.assertNotIn("python .poc/demo/actions_history.py", ledger_only_block)
        self.assertIn('if [[ "$HISTORY_OPT_IN" != "true" && "$REAL_DATA_OPT_IN" != "true" ]]', workflow)
        self.assertIn('"${history_args[@]}"', workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)

    def test_internal_pages_runbook_matches_the_workflow_gates(self):
        guide = (ROOT / "docs/how-to/enable-private-pages-demo.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
        analysis = (ROOT / ".github/workflows/poc-analysis.yml").read_text(encoding="utf-8")
        self.assertIn("GitHub Enterprise Cloud", guide)
        self.assertIn("PAGES_ACTIONS_HISTORY_ENABLED", guide)
        self.assertIn("PAGES_REAL_RUN_DATA_ENABLED", guide)
        self.assertIn("select the default branch (`main`)", guide)
        self.assertIn("poc-database", guide)
        self.assertIn('repository_visibility not in {"private", "internal"}', (ROOT / ".poc/demo/pages_visibility.py").read_text(encoding="utf-8"))
        self.assertIn("public: false", guide)
        self.assertIn("workflow_run", workflow)
        self.assertIn("contents: write", analysis)
        self.assertIn("how-to/enable-private-pages-demo.md", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"))

    def test_static_workflow_links_follow_clone_repository_and_validate_name(self):
        site = self.base / "site"
        demo = site / "demo"
        demo.mkdir(parents=True)
        links = "".join(f'<a id="{key}" href="#">workflow</a>' for key in (
            "demo-open-analysis", "demo-open-evaluation", "demo-open-functional", "demo-guide-analysis", "demo-guide-evaluation", "demo-guide-functional"))
        (demo / "index.html").write_text(links, encoding="utf-8")
        functional = site / "functional-analysis-demo"
        functional.mkdir()
        (functional / "index.html").write_text('<a id="functional-analysis-workflow" href="#">workflow</a><a id="functional-analysis-workflow-step" href="#">workflow</a>', encoding="utf-8")
        prepare_site(site, "example-org/adr-platform")
        result = (demo / "index.html").read_text(encoding="utf-8")
        self.assertEqual(result.count("https://github.com/example-org/adr-platform/actions/workflows/poc-analysis.yml"), 2)
        self.assertEqual(result.count("https://github.com/example-org/adr-platform/actions/workflows/poc-evaluation.yml"), 2)
        self.assertEqual(result.count("https://github.com/example-org/adr-platform/actions/workflows/functional-analysis-demo.yml"), 2)
        functional_result = (functional / "index.html").read_text(encoding="utf-8")
        self.assertEqual(functional_result.count('href="https://github.com/example-org/adr-platform/actions/workflows/functional-analysis-demo.yml"'), 2)
        with self.assertRaisesRegex(ValueError, "owner/name"):
            prepare_site(site, "https://example.com/repo")

    def test_real_history_projection_includes_run_events_and_redacts_evidence_literals(self):
        runs_path = self.db / "runs.csv"
        with runs_path.open(newline="", encoding="utf-8") as handle:
            run_rows = list(csv.DictReader(handle))
            run_header = list(run_rows[0])
        run_rows[0]["github_run_id"] = "864209"
        run_rows[0]["run_id"] = run_rows[0]["run_id"].rsplit("-", 1)[0] + "-2"
        runs_path.write_text(
            ",".join(run_header) + "\n" + ",".join('"' + row[key].replace('"', '""') + '"' for key in run_header for row in [run_rows[0]]) + "\n",
            encoding="utf-8",
        )
        for table in ("artifacts", "run_events", "evidence", "observations", "collection_reports", "confidence_assessments", "confidence_components", "assessment_evidence_links", "findings"):
            path = self.db / f"{table}.csv"
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                header = reader.fieldnames
                rows = list(reader)
            for row in rows:
                row["run_id"] = run_rows[0]["run_id"]
            path.write_text(
                ",".join(header) + "\n" + "\n".join(
                    ",".join('"' + row[key].replace('"', '""') + '"' for key in header) for row in rows
                ) + "\n", encoding="utf-8",
            )
        evidence_path = self.db / "evidence.csv"
        with evidence_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            header = list(rows[0])
        rows[0]["excerpt"] = 'provider.assess("CANARY-PAGES-PRIVATE-LITERAL")'
        rows[0]["sha256"] = hashlib.sha256(rows[0]["excerpt"].encode("utf-8")).hexdigest()
        evidence_path.write_text(
            ",".join(header) + "\n" + "\n".join(
                ",".join('"' + row[key].replace('"', '""') + '"' for key in header) for row in rows
            ) + "\n", encoding="utf-8",
        )
        snapshot = build_history_snapshot(self.db)
        self.assertEqual(snapshot["schema_version"], "adr-demo-history-v1")
        self.assertEqual(snapshot["run_count"], 1)
        run = snapshot["runs"][0]
        self.assertTrue(run["stages"])
        self.assertTrue(run["confidence"]["components"])
        self.assertTrue(any(item["redacted"] for item in run["evidence"]))
        self.assertNotIn("CANARY-PAGES-PRIVATE-LITERAL", json.dumps(snapshot))
        self.assertTrue(run["workflow_url"].startswith("https://github.com/tyler-beach/Platform/actions/runs/"))

    def test_real_history_rejects_invalid_or_ambiguous_artifact_provenance(self):
        mutations = (
            ("artifacts", lambda rows: rows[0].update(artifact_id=""), "artifact ID"),
            ("artifacts", lambda rows: rows[0].update(sha256="not-a-digest"), "SHA-256"),
            ("artifacts", lambda rows: rows.append(dict(rows[0])), "duplicate artifact ID"),
            ("artifacts", lambda rows: rows.append({**rows[0], "artifact_id": "second-artifact"}), "duplicate artifact path"),
            ("evidence", lambda rows: rows[0].update(artifact_id="missing-artifact"), "unknown artifact ID"),
            ("evidence", lambda rows: rows[0].update(path="other/file.go"), "path does not match"),
            ("evidence", lambda rows: rows[0].update(sha256="not-a-digest"), "excerpt SHA-256"),
            ("evidence", lambda rows: rows[0].update(sha256="0" * 64), "excerpt SHA-256 mismatch"),
        )
        for table, mutation, message in mutations:
            with self.subTest(table=table, message=message):
                path = self.db / f"{table}.csv"
                original = path.read_bytes()
                try:
                    self._rewrite_table(table, mutation)
                    with self.assertRaisesRegex(ValueError, message):
                        build_history_snapshot(self.db)
                finally:
                    path.write_bytes(original)

    def test_real_history_requires_observation_source_ref_to_match_artifact(self):
        mutations = (
            lambda source: source.update(artifact_id="missing-artifact"),
            lambda source: source.update(path="other/file.yaml"),
            lambda source: source.update(sha256="0" * 64),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                path = self.db / "observations.csv"
                original = path.read_bytes()
                try:
                    def corrupt(rows):
                        source = json.loads(rows[0]["source_ref_json"])
                        mutation(source)
                        rows[0]["source_ref_json"] = json.dumps(source, sort_keys=True)
                    self._rewrite_table("observations", corrupt)
                    with self.assertRaisesRegex(ValueError, "observation source reference"):
                        build_history_snapshot(self.db)
                finally:
                    path.write_bytes(original)

    def test_real_history_requires_conclusive_findings_to_resolve_cited_evidence(self):
        mutations = (
            lambda rows: rows[0].update(outcome="supported_deviation", evidence_ids_json="[]"),
            lambda rows: rows[0].update(outcome="supported_deviation", evidence_ids_json='["missing-evidence"]'),
        )
        path = self.db / "findings.csv"
        original = path.read_bytes()
        try:
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    path.write_bytes(original)
                    self._rewrite_table("findings", mutation)
                    with self.assertRaisesRegex(ValueError, "finding evidence"):
                        build_history_snapshot(self.db)
        finally:
            path.write_bytes(original)

    def test_real_history_preserves_exact_source_and_excerpt_hashes(self):
        snapshot = build_history_snapshot(self.db)
        run = snapshot["runs"][0]
        with (self.db / "artifacts.csv").open(newline="", encoding="utf-8") as handle:
            artifact_by_id = {row["artifact_id"]: row for row in csv.DictReader(handle)}
        with (self.db / "evidence.csv").open(newline="", encoding="utf-8") as handle:
            evidence_by_id = {row["evidence_id"]: row for row in csv.DictReader(handle)}
        evidence_row = next(row for row in run["evidence"] if row["excerpt"])
        source = artifact_by_id[evidence_by_id[evidence_row["id"]]["artifact_id"]]
        self.assertEqual(evidence_row["source_sha256"], source["sha256"])
        self.assertEqual(evidence_row["recorded_excerpt_sha256"], hashlib.sha256(evidence_row["excerpt"].encode()).hexdigest())
        observation = run["observations"][0]
        self.assertEqual(observation["source_sha256"], artifact_by_id[observation["artifact_id"]]["sha256"])

    def test_real_history_projection_bounds_output_and_refuses_traversal_paths(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 50"):
            build_history_snapshot(self.db, limit=51)
        artifacts = self.db / "artifacts.csv"
        contents = artifacts.read_text(encoding="utf-8")
        artifacts.write_text(contents.replace(".poc/fixtures/go/", "../private/", 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsafe source path"):
            build_history_snapshot(self.db)

    def test_real_history_uses_cloned_repo_identity_and_allowlists_actions_fields(self):
        actions = {
            "schema_version": "adr-demo-actions-v1", "available": True,
            "repository": "example-org/adr-platform",
            "runs": [{"id": 123, "run_number": 7, "run_attempt": 1,
                      "html_url": "https://github.com/example-org/adr-platform/actions/runs/123",
                      "jobs": [], "authorization": "secret-canary", "payload": "prompt-canary"}],
        }
        snapshot = build_history_snapshot(self.db, actions_history=actions)
        self.assertEqual(snapshot["repository"], "example-org/adr-platform")
        self.assertNotIn("secret-canary", json.dumps(snapshot))
        self.assertNotIn("prompt-canary", json.dumps(snapshot))

    def test_real_history_requires_organization_private_or_internal_pages_and_explicit_opt_in(self):
        self.assertFalse(real_data_export_enabled("public", "Organization", True, "false"))
        self.assertTrue(real_data_export_enabled("private", "Organization", False, "true"))
        self.assertTrue(real_data_export_enabled("internal", "Organization", False, "true"))
        with self.assertRaisesRegex(ValueError, "private or internal"):
            real_data_export_enabled("public", "Organization", False, "true")
        with self.assertRaisesRegex(ValueError, "organization-owned"):
            real_data_export_enabled("private", "User", False, "true")
        with self.assertRaisesRegex(ValueError, "Pages API"):
            real_data_export_enabled("internal", "Organization", True, "true")
        with self.assertRaisesRegex(ValueError, "Pages API"):
            real_data_export_enabled("internal", "Organization", None, "true")

    def test_actions_history_has_its_own_opt_in_and_same_private_pages_gate(self):
        self.assertFalse(actions_history_export_enabled("internal", "Organization", False, "false"))
        self.assertTrue(actions_history_export_enabled("internal", "Organization", False, "true"))
        self.assertFalse(actions_history_export_enabled("internal", "Organization", False, "TRUE"))
        with self.assertRaisesRegex(ValueError, "private or internal"):
            actions_history_export_enabled("public", "Organization", False, "true")
        with self.assertRaisesRegex(ValueError, "organization-owned"):
            actions_history_export_enabled("private", "User", False, "true")
        with self.assertRaisesRegex(ValueError, "Pages API"):
            actions_history_export_enabled("private", "Organization", True, "true")

    def test_history_snapshot_can_contain_actions_metadata_without_ledger_rows(self):
        sys.path.insert(0, str(ROOT / ".poc"))
        from store import CsvStore

        empty_db = self.base / "empty-ledger"
        CsvStore(empty_db)
        actions = {
            "schema_version": "adr-demo-actions-v1", "available": True,
            "repository": "example-org/adr-platform",
            "runs": [{"id": 789, "run_number": 12, "run_attempt": 1, "name": "Functional Analysis Demo",
                      "workflow_file": "functional-analysis-demo.yml", "workflow_name": "Functional Analysis Demo",
                      "event": "workflow_dispatch", "status": "completed", "conclusion": "success",
                      "head_branch": "main", "head_sha": "b" * 40,
                      "html_url": "https://github.com/example-org/adr-platform/actions/runs/789",
                      "created_at": "2026-10-17T10:00:00Z", "updated_at": "2026-10-17T10:01:00Z", "jobs": []}],
        }
        snapshot = build_history_snapshot(empty_db, actions_history=actions)
        self.assertTrue(snapshot["api_history_available"])
        self.assertEqual(snapshot["runs"], [])
        self.assertEqual(snapshot["workflow_runs"][0]["id"], 789)

    def test_internal_actions_history_fetch_is_bounded_and_contains_only_status_metadata(self):
        seen = []
        def fake_fetch(path):
            seen.append(path)
            if "/workflows/" in path:
                if "poc-analysis.yml" in path:
                    workflow, run_id = "poc-analysis.yml", 123
                elif "poc-evaluation.yml" in path:
                    workflow, run_id = "poc-evaluation.yml", 456
                else:
                    workflow, run_id = "functional-analysis-demo.yml", 789
                return {"workflow_runs": [{
                    "id": run_id, "run_number": 7, "run_attempt": 2, "name": "Demo", "event": "workflow_dispatch",
                    "status": "completed", "conclusion": "success", "head_branch": "main", "head_sha": "a" * 40,
                    "html_url": f"https://github.com/tyler-beach/Platform/actions/runs/{run_id}",
                    "created_at": "2026-10-17T10:00:00Z", "updated_at": "2026-10-17T10:01:00Z",
                }]}
            return {"jobs": [{"id": 900, "name": "PoC analysis", "status": "completed", "conclusion": "success",
                               "steps": [{"number": 1, "name": "Run mock", "status": "completed", "conclusion": "success"}]}]}
        history = collect_history(fake_fetch, limit=1)
        self.assertTrue(history["available"])
        self.assertEqual(len(history["runs"]), 3)
        self.assertTrue(any("attempts/2/jobs" in path for path in seen))
        self.assertNotIn("Authorization", json.dumps(history))
        self.assertEqual(history["runs"][0]["jobs"][0]["steps"][0]["name"], "Run mock")

    def test_functional_analysis_workflow_is_projected_without_artifacts_or_source(self):
        seen = []

        def fake_fetch(path):
            seen.append(path)
            if "/workflows/" in path:
                if "functional-analysis-demo.yml" not in path:
                    return {"workflow_runs": []}
                return {"workflow_runs": [{
                    "id": 789, "run_number": 12, "run_attempt": 1, "name": "Functional Analysis Demo",
                    "event": "workflow_dispatch", "status": "completed", "conclusion": "success",
                    "head_branch": "main", "head_sha": "b" * 40,
                    "html_url": "https://github.com/example-org/adr-platform/actions/runs/789",
                    "created_at": "2026-10-17T10:00:00Z", "updated_at": "2026-10-17T10:01:00Z",
                    "artifacts_url": "https://api.github.com/private-artifacts", "source": "do-not-export",
                }]}
            return {"jobs": [{"id": 901, "name": "2 · Tree-sitter and document analysis", "status": "completed",
                               "conclusion": "success", "steps": [{"number": 1, "name": "Parse selected source",
                               "status": "completed", "conclusion": "success", "source": "do-not-export"}]}],
                    "artifacts": [{"name": "functional-analysis-demo", "url": "do-not-export"}]}

        history = collect_history(fake_fetch, limit=1, repository="example-org/adr-platform")
        demo_runs = [run for run in history["runs"] if run["workflow_file"] == "functional-analysis-demo.yml"]
        self.assertEqual(len(demo_runs), 1)
        self.assertEqual(demo_runs[0]["html_url"], "https://github.com/example-org/adr-platform/actions/runs/789")
        self.assertEqual(demo_runs[0]["jobs"][0]["name"], "2 · Tree-sitter and document analysis")
        self.assertFalse(any("artifacts" in path or "do-not-export" in path for path in seen))
        encoded = json.dumps(history)
        self.assertNotIn("do-not-export", encoded)
        self.assertNotIn("artifacts_url", encoded)

    def test_internal_actions_history_ignores_untrusted_run_urls(self):
        def fake_fetch(path):
            if "/workflows/" in path:
                return {"workflow_runs": [{"id": 123, "run_number": 1, "status": "completed",
                                            "html_url": "https://evil.invalid/run"}]}
            self.fail("untrusted API URL must be rejected before fetching its jobs")
        history = collect_history(fake_fetch, limit=1)
        self.assertEqual(history["runs"], [])

    def test_internal_actions_history_uses_the_private_clone_repository_identity(self):
        def fake_fetch(path):
            if "/workflows/" in path:
                if "poc-analysis.yml" in path:
                    run_id = 123
                elif "poc-evaluation.yml" in path:
                    run_id = 456
                else:
                    run_id = 789
                return {"workflow_runs": [{
                    "id": run_id, "run_number": 1, "status": "completed",
                    "html_url": f"https://github.com/example-org/adr-platform/actions/runs/{run_id}",
                }]}
            return {"jobs": []}
        history = collect_history(fake_fetch, limit=1, repository="example-org/adr-platform")
        self.assertEqual(history["repository"], "example-org/adr-platform")
        self.assertEqual(len(history["runs"]), 3)
        with self.assertRaisesRegex(ValueError, "owner/name"):
            collect_history(fake_fetch, limit=1, repository="https://example.com/repo")


if __name__ == "__main__":
    unittest.main()
