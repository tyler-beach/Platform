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
sys.path.insert(0, str(ROOT / ".poc"))
sys.path.insert(0, str(ROOT / ".poc" / "evaluation"))

from store import CsvStore, SCHEMAS


class POCWorkflowAuditTests(unittest.TestCase):
    def test_legacy_tables_keep_headers_and_additive_audit_tables_exist(self):
        expected_new_tables = {"observations", "collection_reports"}
        self.assertTrue(expected_new_tables.issubset(SCHEMAS))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy_headers = {}
            for path in (ROOT / ".poc-db").glob("*.csv"):
                shutil.copy2(path, root / path.name)
                with path.open(newline="", encoding="utf-8") as handle:
                    legacy_headers[path.stem] = next(csv.reader(handle))
            store = CsvStore(root)
            for name, columns in legacy_headers.items():
                with (root / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
                    self.assertEqual(next(csv.reader(handle)), columns)
            self.assertTrue(all((root / f"{name}.csv").is_file() for name in expected_new_tables))
            store.append("observations", {
                "observation_id": "obs:one", "run_id": "run-one", "schema_version": "source-observation-v1",
                "evidence_id": "run-one:evidence-1", "predicate": "configuration.property",
                "subject_json": {"id": "config:one"}, "value_json": 7200,
                "source_ref_json": {"artifact_id": "a1", "version": "sha256:abc", "sha256": "abc", "locator": {"line": 4}},
                "collector_json": {"version": "structured-config-v1"}, "resolution_json": {"status": "direct"},
                "evidence_class": "declared_configuration", "redacted": False,
            })
            row = store.rows("observations")[0]
            self.assertEqual(row["run_id"], "run-one")
            self.assertEqual(json.loads(row["source_ref_json"])["version"], "sha256:abc")

    def test_configuration_only_cli_persists_confidence_evidence_and_coverage(self):
        with tempfile.TemporaryDirectory(prefix="poc-audit-", dir=ROOT / ".poc") as workspace:
            base = Path(workspace)
            (base / "config.yaml").write_text(
                "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: auth\ndata:\n  maxTokenLifetimeSeconds: 7200\n  apiToken: CANARY-DO-NOT-PERSIST\n",
                encoding="utf-8",
            )
            (base / "ADR.md").write_text(
                "# Authentication token lifetime\n\nAuthentication tokens must expire within 3600 seconds.\n",
                encoding="utf-8",
            )
            (base / "unparsed.tf").write_text('resource "unsupported" "example" {}\n', encoding="utf-8")
            db = base / "db"
            output = base / "runs"
            command = [
                sys.executable, str(ROOT / ".poc/run.py"), "--source", str(base), "--config-source", str(base),
                "--comparison", "code-diff", "--provider", "mock", "--run-id", "audit-e2e-test",
                "--db-dir", str(db), "--out-dir", str(output), "--adr-path", str(base / "ADR.md"),
            ]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("CANARY-DO-NOT-PERSIST", result.stdout + result.stderr)
            run_dir = output / "audit-e2e-test"
            self.assertTrue((run_dir / "report.md").is_file())
            self.assertTrue((run_dir / "confidence.json").is_file())
            self.assertTrue((run_dir / "observations.json").is_file())
            observations = json.loads((run_dir / "observations.json").read_text(encoding="utf-8"))["observations"]
            self.assertTrue(any(item.get("redacted") for item in observations))
            store = CsvStore(db)
            observation_rows = store.rows("observations")
            self.assertTrue(observation_rows)
            ttl_row = next(row for row in observation_rows if row["predicate"] == "configuration.property" and "maxTokenLifetimeSeconds" in row["source_ref_json"])
            self.assertEqual(json.loads(ttl_row["value_json"]), 7200)
            self.assertTrue(store.rows("collection_reports"))
            self.assertTrue(store.rows("confidence_assessments"))
            components = store.rows("confidence_components")
            self.assertTrue(components)
            self.assertIn("observation_resolution", {row["dimension"] for row in components})
            findings = store.rows("findings")
            self.assertEqual(findings[0]["outcome"], "inconclusive")
            self.assertTrue(any(row["stage"] == "source_collection" and row["status"] == "partial" for row in store.rows("run_events")))
            self.assertEqual(store.rows("collection_reports")[0]["complete"], "False")
            stored = [json.loads(row["source_ref_json"]) for row in store.rows("observations")]
            self.assertTrue(all(source["artifact_id"] and source["version"].startswith("sha256:") and source["sha256"] for source in stored))
            self.assertTrue(all("CANARY-DO-NOT-PERSIST" not in json.dumps(row) for row in store.rows("observations")))
            persisted_files = [*run_dir.rglob("*"), *db.glob("*.csv")]
            for path in persisted_files:
                if path.is_file():
                    self.assertNotIn("CANARY-DO-NOT-PERSIST", path.read_text(encoding="utf-8"))

    def test_language_none_is_rejected_for_code_source(self):
        with tempfile.TemporaryDirectory(prefix="poc-code-no-language-", dir=ROOT / ".poc") as workspace:
            base = Path(workspace)
            (base / "main.py").write_text("def handle():\n    return True\n", encoding="utf-8")
            (base / "ADR.md").write_text("Requests must be authenticated.\n", encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(ROOT / ".poc/run.py"), "--source", str(base), "--comparison", "code-diff",
                "--provider", "mock", "--run-id", "missing-language", "--db-dir", str(base / "db"),
                "--out-dir", str(base / "runs"), "--adr-path", str(base / "ADR.md"),
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--language is required when source code is present", result.stderr)
            events = CsvStore(base / "db").rows("run_events")
            self.assertFalse(any(row["stage"] == "source_collection" and row["event_type"] == "complete" for row in events))

    def test_code_literals_are_redacted_from_all_run_artifacts_and_csv(self):
        with tempfile.TemporaryDirectory(prefix="poc-code-redaction-", dir=ROOT / ".poc") as workspace:
            base = Path(workspace)
            code = base / "main.py"
            code.write_text(
                'def handle(provider):\n    return provider.assess("CANARY-CODE-SECRET")\n', encoding="utf-8"
            )
            adr = base / "ADR.md"
            adr.write_text("Provider calls must use the approved client.\n", encoding="utf-8")
            db = base / "db"
            output = base / "runs"
            result = subprocess.run([
                sys.executable, str(ROOT / ".poc/run.py"), "--source", str(base), "--language", "python",
                "--comparison", "code-diff", "--provider", "mock", "--run-id", "code-redaction-test",
                "--db-dir", str(db), "--out-dir", str(output), "--adr-path", str(adr), "--root-function", "handle",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            all_outputs = [*output.rglob("*"), *db.glob("*.csv")]
            for path in all_outputs:
                if path.is_file():
                    self.assertNotIn("CANARY-CODE-SECRET", path.read_text(encoding="utf-8"))
            self.assertNotIn("CANARY-CODE-SECRET", result.stdout + result.stderr)

    def test_github_workflow_exposes_optional_language_and_configuration_root(self):
        workflow = (ROOT / ".github/workflows/poc-analysis.yml").read_text(encoding="utf-8")
        self.assertIn("none", workflow)
        self.assertIn("config_source", workflow)


class ADREvaluationCorpusTests(unittest.TestCase):
    def test_manifest_has_50_unique_natural_language_adrs_and_pinned_facts(self):
        from evaluate_adr_corpus import load_cases, run_audit, validate_case

        cases = load_cases()
        self.assertEqual(len(cases), 50)
        self.assertEqual(len({case["case_id"] for case in cases}), 50)
        domains = {case["domain"] for case in cases}
        self.assertTrue({"availability", "authentication", "authorization", "encryption", "data_management", "network_security", "observability", "resilience_operations"}.issubset(domains))
        for case in cases:
            validate_case(case)
        result = run_audit()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["evidence_collection"], {"checked": 35, "matched": 35, "accuracy": 1.0})
        self.assertEqual(result["unsupported_cases_remaining_inconclusive"], 15)
        self.assertEqual(result["semantic_model_quality"], "not_evaluated; no model invoked")


if __name__ == "__main__":
    unittest.main()
