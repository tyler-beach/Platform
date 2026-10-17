from __future__ import annotations

import csv
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
from pages_visibility import real_data_export_enabled
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

    def test_snapshot_contains_explorable_allowlisted_demo_outputs(self):
        snapshot = build_snapshot(self.db, self.run_dir, self.fixture)
        self.assertEqual(snapshot["schema_version"], "adr-demo-run-v1")
        self.assertEqual(snapshot["sample"]["provider"], "mock")
        self.assertTrue(snapshot["sample"]["synthetic"])
        self.assertGreaterEqual(len(snapshot["stages"]), 6)
        self.assertTrue(snapshot["evidence"])
        self.assertTrue(snapshot["confidence"]["components"])
        self.assertIn("not a calibrated probability", snapshot["confidence"]["interpretation"].lower())
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
        for link in ("demo-open-analysis", "demo-open-evaluation", "demo-guide-analysis", "demo-guide-evaluation"):
            self.assertIn(f'id="{link}"', page)
        self.assertNotIn("https://github.com/tyler-beach/Platform/actions/workflows/", page)
        self.assertIn("aria-live", page)
        self.assertIn("prefers-reduced-motion: reduce", styles)
        self.assertIn("demo/index.md", config)
        self.assertIn('textContent', javascript)
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
        self.assertIn('workflows: ["ADR Deviation PoC Analysis", "ADR Deviation Labeled Evaluation"]', workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("github.event.workflow_run.event != 'pull_request'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("Resolve this repository's Pages and source URLs", workflow)
        self.assertIn("prepare_site.py", workflow)
        self.assertIn("PAGES_REAL_RUN_DATA_ENABLED", workflow)
        self.assertIn("/pages", workflow)
        self.assertIn("ADR_REPO_URL", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        self.assertIn("ADR_REPO_NAME", workflow)

    def test_static_workflow_links_follow_clone_repository_and_validate_name(self):
        site = self.base / "site"
        demo = site / "demo"
        demo.mkdir(parents=True)
        links = "".join(f'<a id="{key}" href="#">workflow</a>' for key in (
            "demo-open-analysis", "demo-open-evaluation", "demo-guide-analysis", "demo-guide-evaluation"))
        (demo / "index.html").write_text(links, encoding="utf-8")
        prepare_site(site, "example-org/adr-platform")
        result = (demo / "index.html").read_text(encoding="utf-8")
        self.assertEqual(result.count("https://github.com/example-org/adr-platform/actions/workflows/poc-analysis.yml"), 2)
        self.assertEqual(result.count("https://github.com/example-org/adr-platform/actions/workflows/poc-evaluation.yml"), 2)
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

    def test_real_history_requires_private_repository_private_pages_and_explicit_opt_in(self):
        self.assertFalse(real_data_export_enabled("public", True, "false"))
        self.assertTrue(real_data_export_enabled("private", False, "true"))
        with self.assertRaisesRegex(ValueError, "repository visibility=private"):
            real_data_export_enabled("public", False, "true")
        with self.assertRaisesRegex(ValueError, "Pages API"):
            real_data_export_enabled("private", True, "true")
        with self.assertRaisesRegex(ValueError, "Pages API"):
            real_data_export_enabled("private", None, "true")

    def test_internal_actions_history_fetch_is_bounded_and_contains_only_status_metadata(self):
        seen = []
        def fake_fetch(path):
            seen.append(path)
            if "/workflows/" in path:
                workflow = "poc-analysis.yml" if "poc-analysis" in path else "poc-evaluation.yml"
                run_id = 123 if workflow == "poc-analysis.yml" else 456
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
        self.assertEqual(len(history["runs"]), 2)
        self.assertTrue(any("attempts/2/jobs" in path for path in seen))
        self.assertNotIn("Authorization", json.dumps(history))
        self.assertEqual(history["runs"][0]["jobs"][0]["steps"][0]["name"], "Run mock")

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
                workflow = "poc-analysis.yml" if "poc-analysis" in path else "poc-evaluation.yml"
                run_id = 123 if workflow == "poc-analysis.yml" else 456
                return {"workflow_runs": [{
                    "id": run_id, "run_number": 1, "status": "completed",
                    "html_url": f"https://github.com/example-org/adr-platform/actions/runs/{run_id}",
                }]}
            return {"jobs": []}
        history = collect_history(fake_fetch, limit=1, repository="example-org/adr-platform")
        self.assertEqual(history["repository"], "example-org/adr-platform")
        self.assertEqual(len(history["runs"]), 2)
        with self.assertRaisesRegex(ValueError, "owner/name"):
            collect_history(fake_fetch, limit=1, repository="https://example.com/repo")


if __name__ == "__main__":
    unittest.main()
