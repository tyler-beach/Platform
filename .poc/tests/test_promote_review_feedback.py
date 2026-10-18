from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "review_sampling"))
from promote_review_feedback import export_candidates


def event(event_id, **overrides):
    base = {
        "event_id": event_id, "event_type": "review.adjudicated",
        "unit_id": "req-1:artifact-sha:run-1", "analysis_run_id": "run-1",
        "analysis_version": "pipeline-v1+sha256:abc", "actor_id": "adjudicator-1",
        "adjudicator_id": "adjudicator-1", "timestamp": "2026-10-18T10:00:00Z",
        "disposition": "confirmed_deviation", "reason_code": "evidence_supports_claim",
        "evidence_refs": ["EV-REQ", "EV-OBS"], "rationale_summary": "Independent adjudication confirmed the mismatch.",
        "adjudication_status": "adjudicated", "promotion_status": "approved",
        "evaluation_label": "deviation", "evaluation_split": "candidate_train",
        "feedback_route": "inference_evaluation", "event_hash": "f" * 64,
    }
    base.update(overrides)
    return base


class FeedbackPromotionTests(unittest.TestCase):
    def test_only_approved_adjudicated_training_candidates_export(self):
        rows = [
            event("approved"),
            event("disposition-only", event_type="review.dispositioned"),
            event("pending", promotion_status="pending"),
            event("holdout", evaluation_split="holdout"),
            event("bad-label", evaluation_label="maybe"),
        ]
        result = export_candidates(rows)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["source_review_event_id"], "approved")
        self.assertEqual(result["candidates"][0]["promotion_state"], "candidate_pending_corpus_review")
        self.assertEqual(result["excluded_counts"]["not_adjudicated"], 1)
        self.assertEqual(result["excluded_counts"]["not_approved"], 1)
        self.assertEqual(result["excluded_counts"]["holdout_or_eval_split"], 1)
        self.assertEqual(result["excluded_counts"]["invalid_label"], 1)

    def test_holdout_is_never_exported_even_if_approved(self):
        result = export_candidates([event("holdout", evaluation_split="holdout")])
        self.assertEqual(result["candidate_count"], 0)

    def test_missing_split_never_defaults_to_training(self):
        row = event("missing-split")
        del row["evaluation_split"]
        result = export_candidates([row])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["excluded_counts"]["holdout_or_eval_split"], 1)

    def test_missing_adjudicator_provenance_is_excluded(self):
        row = event("missing-adjudicator")
        del row["adjudicator_id"]
        result = export_candidates([row])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["excluded_counts"]["missing_provenance"], 1)

    def test_candidate_has_provenance_and_no_source_excerpt(self):
        candidate = export_candidates([event("one")])["candidates"][0]
        self.assertEqual(candidate["analysis_version"], "pipeline-v1+sha256:abc")
        self.assertEqual(candidate["evidence_refs"], ["EV-REQ", "EV-OBS"])
        self.assertIn("source_event_hash", candidate)
        self.assertNotIn("source_excerpt", candidate)
        self.assertNotIn("raw_prompt", candidate)

    def test_unknown_feedback_route_is_excluded(self):
        result = export_candidates([event("route", feedback_route="arbitrary")])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["excluded_counts"]["missing_route"], 1)

    def test_export_fingerprint_is_stable(self):
        rows = [event("one"), event("two")]
        self.assertEqual(export_candidates(rows), export_candidates(list(reversed(rows))))


if __name__ == "__main__":
    unittest.main()
