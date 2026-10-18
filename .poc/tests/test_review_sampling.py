from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "review_sampling" / "sample.py"
SPEC = importlib.util.spec_from_file_location("review_sample", MODULE)
review_sample = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(review_sample)


class ReviewSamplingTests(unittest.TestCase):
    def frame(self):
        return [
            {"unit_id": "u1", "outcome": "deviation", "evidence_band": "high"},
            {"unit_id": "u2", "outcome": "deviation", "evidence_band": "high"},
            {"unit_id": "u3", "outcome": "deviation", "evidence_band": "high", "risk_flags": ["STALE_SOURCE"]},
            {"unit_id": "u4", "outcome": "no_deviation", "evidence_band": "moderate"},
            {"unit_id": "u5", "outcome": "no_deviation", "evidence_band": "moderate"},
            {"unit_id": "u6", "outcome": "inconclusive", "evidence_band": "low", "impact": "critical"},
        ]

    def test_seed_and_frame_order_are_reproducible(self):
        rows = self.frame()
        first = review_sample.build_batch(rows, seed="pilot-1", per_stratum=1)
        second = review_sample.build_batch(list(reversed(rows)), seed="pilot-1", per_stratum=1)
        self.assertEqual(first, second)

    def test_probability_is_per_stratum_and_weights_are_inverse(self):
        batch = review_sample.build_batch(self.frame(), seed="pilot-1", per_stratum=1)
        selected = [item for item in batch["probability_sample"] if item["outcome"] == "deviation"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["stratum_population_count"], 3)
        self.assertAlmostEqual(selected[0]["inclusion_probability"], 1 / 3)
        self.assertAlmostEqual(selected[0]["design_weight"], 3.0)

    def test_risk_queue_is_separate_and_does_not_get_sampling_weight(self):
        batch = review_sample.build_batch(self.frame(), seed="pilot-1", per_stratum=1)
        risk = {item["unit_id"]: item for item in batch["risk_sample"]}
        self.assertIn("u3", risk)
        self.assertIn("u6", risk)
        self.assertIsNone(risk["u3"]["population_inclusion_probability"])
        self.assertNotIn("design_weight", risk["u3"])
        self.assertTrue(any("not representative" in item["note"] for item in risk.values()))

    def test_no_duplicate_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.jsonl"
            row = self.frame()[0]
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate unit_id"):
                review_sample.load_frame(path)

    def test_empty_frame_is_valid_and_stable(self):
        batch = review_sample.build_batch([], seed="empty", per_stratum=2)
        self.assertEqual(batch["frame"]["unit_count"], 0)
        self.assertEqual(batch["probability_sample"], [])
        self.assertEqual(batch["risk_sample"], [])


if __name__ == "__main__":
    unittest.main()
