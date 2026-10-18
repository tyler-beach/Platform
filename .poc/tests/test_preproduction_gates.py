from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "evaluation"))
from audit_corpus import audit


class EvaluationCorpusAuditTests(unittest.TestCase):
    def test_current_labeled_corpus_is_structurally_valid_but_not_production_ready(self):
        result = audit(ROOT / ".poc" / "evaluation" / "cases.jsonl")
        self.assertTrue(result["structurally_valid"], result["errors"])
        self.assertGreater(result["case_count"], 0)
        self.assertEqual(sum(result["label_counts"].values()), result["case_count"])
        self.assertTrue(result["readiness_gaps"])
        self.assertIn("does not establish detector accuracy", result["interpretation"])

    def test_duplicate_ids_and_invalid_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cases.jsonl"
            base = '{"case_id":"D-1","title":"Example","gold_label":"deviation","has_normative":true,"behavior":"direct","entry_status":"resolved","dispatch":"static","requirement":"must enqueue","observation":"call","diff_excerpt":"change"}'
            invalid = base.replace('"gold_label":"deviation"', '"gold_label":"maybe"')
            path.write_text(base + "\n" + invalid + "\n", encoding="utf-8")
            result = audit(path)
            self.assertFalse(result["structurally_valid"])
            self.assertEqual(result["duplicate_case_ids"], ["D-1"])
            self.assertTrue(any("unsupported gold_label" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
