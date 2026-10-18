from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "evaluation"))
sys.path.insert(0, str(ROOT / ".poc" / "replay"))
sys.path.insert(0, str(ROOT / ".poc" / "scope"))

from audit_locked_holdout import audit as audit_holdout
from replay_event import replay
from retrieval import load_jsonl


class LockedHoldoutTests(unittest.TestCase):
    def test_locked_holdout_is_integral_unlabeled_and_quarantined(self):
        result = audit_holdout()
        self.assertTrue(result["structurally_valid"], result["errors"])
        self.assertEqual(result["case_count"], 4)
        self.assertFalse(result["labels_are_ground_truth"])
        self.assertEqual(result["status"], "quarantined_pending_independent_adjudication")

    def test_holdout_hash_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root_lock = ROOT / ".poc" / "evaluation" / "holdout-lock.json"
            lock = json.loads(root_lock.read_text(encoding="utf-8"))
            mutated = Path(temp) / "holdout.jsonl"
            mutated.write_text((ROOT / lock["dataset_path"]).read_text(encoding="utf-8") + "\n", encoding="utf-8")
            lock["dataset_path"] = str(mutated)
            lock_path = Path(temp) / "lock.json"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            result = audit_holdout(lock_path)
            self.assertFalse(result["structurally_valid"])
            self.assertTrue(any("fingerprint mismatch" in error for error in result["errors"]))


class ReplayTests(unittest.TestCase):
    def test_event_template_replay_is_deterministic_and_evidence_linked(self):
        event = json.loads((ROOT / ".poc" / "scope" / "event-template.json").read_text(encoding="utf-8"))
        catalog_path = ROOT / ".poc" / "scope" / "adr_catalog.jsonl"
        catalog = load_jsonl(catalog_path)
        import hashlib
        catalog_hash = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
        first = replay(event, catalog, catalog_hash)
        second = replay(event, catalog, catalog_hash)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "pathfinder.replay-report.v1")
        self.assertEqual(len(first["input_sha256"]), 64)
        self.assertEqual(len(first["report_sha256"]), 64)
        self.assertTrue(first["evidence_refs"])
        self.assertIn(first["outcome"], {"deviation", "aligned", "uncertain", "no_applicable_adr"})

    def test_summary_only_event_is_rejected(self):
        event = {
            "repository": "example", "service": "api", "domain": "application",
            "language": "go", "change_summary": "Call provider",
        }
        catalog_path = ROOT / ".poc" / "scope" / "adr_catalog.jsonl"
        with self.assertRaisesRegex(ValueError, "source_observations or exact diff_lines"):
            replay(event, load_jsonl(catalog_path), "0" * 64)


if __name__ == "__main__":
    unittest.main()
