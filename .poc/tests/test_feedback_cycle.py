from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "review_sampling"))
from validate_feedback_cycle import validate_cycle


class FeedbackCycleTests(unittest.TestCase):
    def setUp(self):
        self.batch = {
            "seed": "test-seed",
            "frame": {"fingerprint_sha256": "a" * 64},
            "probability_sample": [{"unit_id": "unit-1", "inclusion_probability": 0.5, "design_weight": 2.0, "selection_reason": "STRATIFIED_RANDOM"}],
            "risk_sample": [],
        }
        self.disposition = {
            "event_id": "review-1", "event_type": "review.dispositioned",
            "unit_id": "unit-1", "actor_id": "reviewer-a", "event_hash": "1" * 64,
        }
        self.adjudication = {
            "event_id": "adjudication-1", "event_type": "review.adjudicated",
            "unit_id": "unit-1", "actor_id": "reviewer-b", "adjudicator_id": "reviewer-b",
            "event_hash": "2" * 64, "adjudication_status": "adjudicated",
        }

    def test_requires_sampled_unit_prior_disposition_and_distinct_adjudicator(self):
        result = validate_cycle([self.disposition, self.adjudication], self.batch)
        self.assertTrue(result["valid"], result["errors"])

    def test_rejects_unreviewed_unit(self):
        result = validate_cycle([dict(self.disposition, unit_id="not-sampled")], self.batch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("not in the supplied sample" in error for error in result["errors"]))

    def test_rejects_same_reviewer_as_adjudicator(self):
        adjudication = dict(self.adjudication, adjudicator_id="reviewer-a")
        result = validate_cycle([self.disposition, adjudication], self.batch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("distinct" in error for error in result["errors"]))

    def test_rejects_adjudication_without_prior_disposition(self):
        result = validate_cycle([self.adjudication], self.batch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("earlier disposition" in error for error in result["errors"]))

    def test_rejects_disposition_that_appears_after_adjudication(self):
        result = validate_cycle([self.adjudication, self.disposition], self.batch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("earlier disposition" in error for error in result["errors"]))

    def test_rejects_invalid_sampling_weight(self):
        batch = {**self.batch, "probability_sample": [{**self.batch["probability_sample"][0], "design_weight": 9.0}]}
        result = validate_cycle([self.disposition, self.adjudication], batch)
        self.assertFalse(result["valid"])
        self.assertTrue(any("reciprocal" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
