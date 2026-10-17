from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "demo"))
sys.path.insert(0, str(ROOT / ".poc"))

from functional_analysis_ledger import execution_only_record, persist_record, project_bundle
from reconcile_functional_analysis import reconcile
from store import CsvStore
from export_site_snapshot import build_history_snapshot


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def make_bundle(*, run_id="123", run_attempt=2, outcome="supported_deviation", check_passed=True,
                adr_bytes=b"ADR: MUST use async execution.\n", code_bytes=b"callProvider()\n",
                duplicate_evidence=False, unknown_citation=False, invalid_declared_code_hash=False, extra_files=None):
    diff_bytes = b"+callProvider()\n"
    files = {"input/adr.md": adr_bytes, "input/handler.go": code_bytes, "input/change.diff": diff_bytes}
    manifest = {
        "manifest_version": "1.1.0", "run_id": str(run_id), "run_attempt": run_attempt,
        "comparison": "code-diff", "sample_case": "deviation", "language": "go",
        "comparison_contract": "implementation_vs_adr", "artifacts": [
            {"artifact_id": "ART-ADR-001", "role": "adr", "path": "input/adr.md", "sha256": sha(adr_bytes), "version": "sha256:" + sha(adr_bytes), "byte_length": len(adr_bytes)},
            {"artifact_id": "ART-CODE-001", "role": "implementation", "path": "input/handler.go", "sha256": ("0" * 64 if invalid_declared_code_hash else sha(code_bytes)), "version": "sha256:" + ("0" * 64 if invalid_declared_code_hash else sha(code_bytes)), "byte_length": len(code_bytes)},
            {"artifact_id": "ART-DIFF-001", "role": "diff", "path": "input/change.diff", "sha256": sha(diff_bytes), "version": "sha256:" + sha(diff_bytes), "byte_length": len(diff_bytes)},
        ],
    }
    evidence = {
        "evidence_contract_version": "1.0.0",
        "items": [
            {"evidence_id": "EV-ADR-001", "artifact_id": "ART-ADR-001", "artifact_version": "sha256:" + sha(adr_bytes), "source_path": "input/adr.md", "locator": {"kind": "source-line", "line_start": 1, "line_end": 1}, "evidence_type": "architectural_constraint", "excerpt": "MUST use async execution."},
            {"evidence_id": "EV-TS-001", "artifact_id": "ART-CODE-001", "artifact_version": "sha256:" + sha(code_bytes), "source_path": "input/handler.go", "locator": {"kind": "tree-sitter-node", "line_start": 1, "line_end": 1, "start_byte": 0, "end_byte": len(code_bytes.rstrip())}, "evidence_type": "syntax_call_site", "excerpt": code_bytes.rstrip().decode()},
        ],
    }
    if duplicate_evidence:
        evidence["items"].append(dict(evidence["items"][0]))
    checks = [{"name": "Pinned source hashes match bundle bytes", "passed": check_passed, "detail": "fixture detail must not be persisted"}]
    citations = ["EV-ADR-001", "EV-TS-001"] + (["EV-UNKNOWN"] if unknown_citation else [])
    files.update({
        "input-manifest.json": json.dumps(manifest).encode(),
        "evidence-package.json": json.dumps(evidence).encode(),
        "mock-model-response.json": json.dumps({"provider": "deterministic-mock", "network_requests": 0, "candidate": {"outcome": outcome, "evidence_ids": citations, "limitations": ["Evidence is insufficient."] if outcome == "inconclusive" else []}}).encode(),
        "validation-result.json": json.dumps({"validation_version": "1.0.0", "status": "passed" if check_passed else "failed", "candidate_outcome": outcome, "checks": checks}).encode(),
        "functional-analysis-report.json": json.dumps({"report_version": "1.0.0", "run_id": str(run_id), "run_attempt": run_attempt, "comparison": "code-diff", "comparison_contract": "implementation_vs_adr", "sample_case": "deviation", "language": "go", "status": "passed" if check_passed else "failed", "actual_outcome": outcome, "evidence_item_count": len(evidence["items"])}).encode(),
    })
    if extra_files:
        files.update(extra_files)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return output.getvalue()


def expected_context(**updates):
    result = {
        "repository": "example-org/adr-platform", "workflow_id": 456,
        "workflow_sha": "a" * 40, "run_id": 123, "run_attempt": 2,
        "event": "workflow_dispatch", "head_branch": "main", "default_branch": "main",
        "execution_status": "completed", "execution_conclusion": "success",
        "artifact_id": 789, "artifact_name": "functional-analysis-demo-123-2",
        "artifact_digest": "sha256:" + "b" * 64,
    }
    result.update(updates)
    return result


class FunctionalAnalysisLedgerTests(unittest.TestCase):
    def test_projects_validated_bundle_to_allowlisted_record_without_source_text(self):
        record = project_bundle(make_bundle(), expected_context())
        self.assertEqual(record["domain_outcome"], "supported_deviation")
        self.assertEqual(record["analysis_state"], "validated")
        self.assertEqual(record["confidence_status"], "unavailable")
        self.assertIn("not confidence", record["confidence_reason"])
        self.assertEqual(len(json.loads(record["source_artifacts_json"])), 3)
        self.assertEqual(len(json.loads(record["evidence_refs_json"])), 2)
        serialized = json.dumps(record).lower()
        self.assertNotIn("must use async", serialized)
        self.assertNotIn("callprovider", serialized)
        self.assertNotIn("fixture detail", serialized)

    def test_rejects_run_attempt_or_event_mismatch_before_projection(self):
        with self.assertRaisesRegex(ValueError, "run identity"):
            project_bundle(make_bundle(run_id="999"), expected_context())
        with self.assertRaisesRegex(ValueError, "default branch"):
            project_bundle(make_bundle(), expected_context(head_branch="feature/demo"))
        with self.assertRaisesRegex(ValueError, "event"):
            project_bundle(make_bundle(), expected_context(event="pull_request"))

    def test_reconciliation_rejects_pull_request_before_artifact_lookup(self):
        class FakeAPI:
            def __init__(self):
                self.artifact_lookups = 0

            def get_json(self, path, query=None):
                if path == "/":
                    return {"full_name": "example-org/adr-platform", "default_branch": "main"}
                if path == "/actions/workflows/functional-analysis-demo.yml":
                    return {"id": 44, "path": ".github/workflows/functional-analysis-demo.yml"}
                if path == "/actions/runs/789/attempts/1":
                    return {"id": 789, "run_attempt": 1, "workflow_id": 44,
                            "event": "pull_request", "head_branch": "feature", "status": "completed",
                            "conclusion": "success", "head_sha": "a" * 40}
                if path.endswith("/artifacts"):
                    self.artifact_lookups += 1
                    return {"artifacts": []}
                raise AssertionError(f"unexpected API path: {path}")

        api = FakeAPI()
        with tempfile.TemporaryDirectory(dir=ROOT / ".poc") as temporary:
            result = reconcile(api, "example-org/adr-platform", Path(temporary) / "db", (789, 1))
        self.assertEqual(result["skipped_untrusted"], 1)
        self.assertEqual(api.artifact_lookups, 0)

    def test_rejects_hash_mismatch_duplicate_ids_unknown_citations_and_failed_validation(self):
        with self.assertRaisesRegex(ValueError, "source hash"):
            project_bundle(make_bundle(invalid_declared_code_hash=True), expected_context())
        duplicate = make_bundle(extra_files={"unused": b""})
        with self.assertRaisesRegex(ValueError, "unknown archive member"):
            project_bundle(duplicate, expected_context())
        with self.assertRaisesRegex(ValueError, "duplicated"):
            project_bundle(make_bundle(duplicate_evidence=True), expected_context())
        with self.assertRaisesRegex(ValueError, "evidence references"):
            project_bundle(make_bundle(unknown_citation=True), expected_context())
        with self.assertRaisesRegex(ValueError, "validation"):
            project_bundle(make_bundle(check_passed=False), expected_context())

    def test_rejects_unsafe_archive_paths_and_oversized_archives(self):
        with self.assertRaisesRegex(ValueError, "unsafe archive path"):
            project_bundle(make_bundle(extra_files={"../outside": b"x"}), expected_context())
        with self.assertRaisesRegex(ValueError, "compressed artifact exceeds"):
            project_bundle(b"x" * (10 * 1024 * 1024 + 1), expected_context())

    def test_execution_only_record_has_no_domain_outcome_or_confidence(self):
        record = execution_only_record(expected_context(execution_conclusion="failure"))
        self.assertEqual(record["execution_status"], "completed")
        self.assertEqual(record["analysis_state"], "not_started")
        self.assertEqual(record["persistence_state"], "execution_only")
        self.assertEqual(record["domain_outcome"], "")
        self.assertEqual(record["confidence_status"], "unavailable")

    def test_unreconciled_success_can_append_validated_revision_without_erasing_history(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".poc") as temporary:
            store = CsvStore(temporary)
            first = execution_only_record(expected_context(), persistence_state="unreconciled")
            self.assertEqual(persist_record(store, first), "persisted")
            validated = project_bundle(make_bundle(), expected_context())
            self.assertEqual(persist_record(store, validated), "updated")
            rows = store.rows("functional_analysis_runs")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["analysis_state"], "unreconciled")
            self.assertEqual(rows[1]["analysis_state"], "validated")
            self.assertEqual(rows[1]["record_revision"], "2")
            self.assertEqual(rows[1]["supersedes_fingerprint"], rows[0]["record_fingerprint"])

    def test_csv_persistence_is_idempotent_and_rejects_identity_collision(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".poc") as temporary:
            store = CsvStore(temporary)
            record = project_bundle(make_bundle(), expected_context())
            self.assertEqual(persist_record(store, record), "persisted")
            self.assertEqual(persist_record(store, record), "duplicate")
            self.assertEqual(len(store.rows("functional_analysis_runs")), 1)

    def test_pages_history_includes_only_allowlisted_functional_analysis_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".poc") as temporary:
            store = CsvStore(Path(temporary) / "db")
            record = project_bundle(make_bundle(), expected_context())
            store.append("functional_analysis_runs", record)
            history = build_history_snapshot(Path(temporary) / "db", repository="example-org/adr-platform")
            self.assertEqual(len(history["runs"]), 1)
            record_view = history["runs"][0]["functional_analysis"]
            self.assertEqual(record_view["domain_outcome"], "supported_deviation")
            self.assertEqual(record_view["confidence_status"], "unavailable")
            serialized = json.dumps(history)
            self.assertNotIn("callProvider", serialized)
            self.assertNotIn("MUST use async", serialized)

    def test_pages_history_rejects_tampered_functional_analysis_fingerprint(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".poc") as temporary:
            store = CsvStore(Path(temporary) / "db")
            record = project_bundle(make_bundle(), expected_context())
            record["domain_outcome"] = "inconclusive"
            store.append("functional_analysis_runs", record)
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                build_history_snapshot(Path(temporary) / "db", repository="example-org/adr-platform")
            changed = project_bundle(make_bundle(outcome="inconclusive"), expected_context())
            with self.assertRaisesRegex(ValueError, "identity collision"):
                persist_record(store, changed)
            self.assertEqual(len(store.rows("functional_analysis_runs")), 1)


if __name__ == "__main__":
    unittest.main()
