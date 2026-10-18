from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "demo"))

import export_paste_eval_snapshot


class PasteEvalSnapshotTests(unittest.TestCase):
    def test_snapshot_is_redacted_and_backbone_labeled(self):
        snapshot = export_paste_eval_snapshot.build_snapshot()
        self.assertEqual(snapshot["schema_version"], "pathfinder-paste-eval-demo-v1")
        self.assertEqual(snapshot["backbone"], "github-issues-actions")
        self.assertTrue(snapshot["synthetic"])
        self.assertGreater(snapshot["observation_count"], 0)
        self.assertTrue(snapshot["extracted_observations"])
        self.assertIn(snapshot["aggregate_status"], {
            "mixed", "deviations_found", "all_aligned", "insufficient_coverage", "not_applicable_only",
        })
        encoded = json.dumps(snapshot)
        self.assertNotIn("sk-live", encoded)
        self.assertNotIn("Sessions expire after 12 minutes", encoded)
        self.assertNotIn("package main", encoded)

    def test_cli_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "paste-eval-snapshot.json"
            rc = export_paste_eval_snapshot.main(["--output", str(out)])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "pathfinder-paste-eval-demo-v1")


if __name__ == "__main__":
    unittest.main()
