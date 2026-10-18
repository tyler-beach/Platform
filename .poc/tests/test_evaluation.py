from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc"))

from evaluation import evaluate
import model


class LabeledEvaluationTests(unittest.TestCase):
    def test_dataset_contains_all_three_gold_labels_and_unique_ids(self):
        cases = evaluate.load_cases()
        ids = [case["case_id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({case["gold_label"] for case in cases}, {"deviation", "no_deviation", "ambiguous"})
        self.assertGreaterEqual(len(cases), 12)

    def test_dataset_fingerprint_is_stable_and_tracks_exact_corpus_bytes(self):
        first = evaluate.dataset_fingerprint()
        second = evaluate.dataset_fingerprint()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertTrue(all(char in "0123456789abcdef" for char in first))

    def test_metrics_include_behavior_breakdown(self):
        rows = [
            {"case_id": "D1", "behavior": "direct_provider", "gold_label": "deviation", "predicted_label": "deviation", "accepted_outcome": "supported_deviation", "score_0_to_100": 80.0},
            {"case_id": "N1", "behavior": "no_provider", "gold_label": "no_deviation", "predicted_label": "no_deviation", "accepted_outcome": "no_deviation_found", "score_0_to_100": 90.0},
        ]
        metrics = evaluate.compute_metrics(rows)
        self.assertEqual(metrics["by_behavior"]["direct_provider"]["exact_three_way_accuracy"], 1.0)
        self.assertEqual(metrics["by_behavior"]["no_provider"]["clear_case_binary_metrics"]["tn"], 1)

    def test_case_builder_pins_excerpt_hashes_and_links_edges(self):
        case = next(c for c in evaluate.load_cases() if c["case_id"] == "D-01")
        context, artifacts = evaluate.build_case_context(case)
        artifact_ids = {row["artifact_id"] for row in artifacts}
        for ev in context["evidence"]:
            self.assertIn(ev["artifact_id"], artifact_ids)
            self.assertEqual(ev["sha256"], evaluate.sha(ev["excerpt"]))
        edge_ids = {edge["edge_id"] for edge in context["graph"]["edges"]}
        cited_edge_ids = {ev["edge_id"] for ev in context["evidence"] if ev.get("edge_id")}
        self.assertEqual(cited_edge_ids, edge_ids)

    def test_supported_finding_below_gate_is_not_counted_as_actionable(self):
        results = [
            {
                "case_id": "D1", "gold_label": "deviation", "predicted_label": "deviation",
                "accepted_outcome": "supported_deviation", "score_0_to_100": 72.0,
            },
            {
                "case_id": "N1", "gold_label": "no_deviation", "predicted_label": "no_deviation",
                "accepted_outcome": "no_deviation_found", "score_0_to_100": 92.0,
            },
            {
                "case_id": "A1", "gold_label": "ambiguous", "predicted_label": "ambiguous",
                "accepted_outcome": "potential_deviation", "score_0_to_100": 55.0,
            },
        ]
        metrics = evaluate.compute_metrics(results)
        sweep = {row["threshold"]: row for row in metrics["review_gate_threshold_sweep"]}
        self.assertEqual(sweep[70]["actionable_findings"], 1)
        self.assertEqual(sweep[80]["actionable_findings"], 0)
        self.assertEqual(sweep[80]["fn"], 1)
        self.assertEqual(metrics["ambiguous_case_escalation_rate"], 1.0)
        self.assertIn("not probabilities", metrics["interpretation"])

    def test_mock_does_not_confuse_local_validator_with_remote_provider(self):
        case = next(c for c in evaluate.load_cases() if c["case_id"] == "N-03")
        context, _ = evaluate.build_case_context(case)
        self.assertEqual(model.mock_assess(context)["outcome"], "no_deviation_found")

    def test_mock_recognizes_explicit_queue_boundary_before_worker_provider(self):
        for case_id in ("N-01", "N-05"):
            with self.subTest(case_id=case_id):
                case = next(c for c in evaluate.load_cases() if c["case_id"] == case_id)
                context, _ = evaluate.build_case_context(case)
                self.assertEqual(model.mock_assess(context)["outcome"], "no_deviation_found")

    def test_mock_escalates_conditional_or_approximate_provider_edges(self):
        for case_id in ("A-02", "A-05", "A-06"):
            with self.subTest(case_id=case_id):
                case = next(c for c in evaluate.load_cases() if c["case_id"] == case_id)
                context, _ = evaluate.build_case_context(case)
                self.assertEqual(model.mock_assess(context)["outcome"], "potential_deviation")


if __name__ == "__main__":
    unittest.main()
