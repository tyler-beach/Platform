from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "compare_reports.py"
SPEC = importlib.util.spec_from_file_location("compare_reports", MODULE_PATH)
compare_reports = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(compare_reports)


def report(fingerprint="a" * 64, provider="mock", accuracy=0.8):
    return {
        "dataset_fingerprint_sha256": fingerprint,
        "analysis_configuration": {"provider": provider, "max_output_tokens": 1000},
        "metrics": {
            "case_count": 20,
            "three_way_correct": int(accuracy * 20),
            "exact_three_way_accuracy": accuracy,
            "clear_case_count": 15,
            "clear_case_decision_coverage": 0.9,
            "ambiguous_case_count": 5,
            "ambiguous_case_escalation_rate": 0.8,
            "by_behavior": {"direct_provider": {"case_count": 4, "exact_three_way_accuracy": accuracy}},
        },
    }


class EvaluationComparisonTests(unittest.TestCase):
    def test_same_fingerprint_and_configuration_is_like_for_like(self):
        result = compare_reports.compare(report(), report(accuracy=0.9))
        self.assertEqual(result["comparison_status"], "like_for_like")
        self.assertAlmostEqual(result["metric_deltas"]["exact_three_way_accuracy"]["delta"], 0.1)

    def test_changed_corpus_is_explicitly_not_like_for_like(self):
        result = compare_reports.compare(report(), report(fingerprint="b" * 64, accuracy=0.9))
        self.assertEqual(result["comparison_status"], "not_like_for_like")
        self.assertFalse(result["same_dataset"])

    def test_changed_provider_is_not_like_for_like(self):
        result = compare_reports.compare(report(), report(provider="anthropic"))
        self.assertEqual(result["comparison_status"], "not_like_for_like")
        self.assertFalse(result["same_analysis_configuration"])

    def test_no_release_threshold_is_applied(self):
        result = compare_reports.compare(report(accuracy=0.9), report(accuracy=0.2))
        self.assertEqual(result["comparison_status"], "like_for_like")
        self.assertIn("No release threshold is applied", result["guardrails"][0])


if __name__ == "__main__":
    unittest.main()
