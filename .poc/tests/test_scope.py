from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE_DIR = ROOT / ".poc" / "scope"
sys.path.insert(0, str(SCOPE_DIR))

import retrieval
import run_scope


class ScopeRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = retrieval.load_jsonl(SCOPE_DIR / "adr_catalog.jsonl")
        cls.scenarios = retrieval.load_jsonl(SCOPE_DIR / "scenarios.jsonl")
        cls.by_id = {row["case_id"]: row for row in cls.scenarios}

    def test_active_metadata_gate_excludes_retired_adr_even_if_words_match(self):
        event = self.by_id["SCOPE-06"]
        result = retrieval.retrieve(event, self.catalog)
        all_candidates = result["selected_adrs"] + result["review_candidates"]
        self.assertNotIn("ADR-006", {candidate["adr_id"] for candidate in all_candidates})
        excluded = {row["adr_id"]: row for row in result["excluded_adrs"]}
        self.assertIn("ADR-006", excluded)
        self.assertTrue(any("inactive lifecycle" in x for x in excluded["ADR-006"]["reasons"]))

    def test_service_and_domain_metadata_gate_is_enforced_before_ranking(self):
        event = dict(self.by_id["SCOPE-01"])
        result = retrieval.retrieve(event, self.catalog)
        candidates = {candidate["adr_id"] for candidate in result["selected_adrs"] + result["review_candidates"]}
        self.assertNotIn("ADR-007", candidates)
        self.assertIn("ADR-001", candidates)

    def test_expected_current_adrs_are_retrieved_for_core_scenarios(self):
        # This is a deliberately small regression corpus; expected retrieval targets
        # are reviewed alongside scenarios.jsonl rather than treated as production stats.
        for case_id in ("SCOPE-01", "SCOPE-02", "SCOPE-03", "SCOPE-04", "SCOPE-05", "SCOPE-08"):
            with self.subTest(case_id=case_id):
                event = self.by_id[case_id]
                result = retrieval.retrieve(event, self.catalog)
                selected = {candidate["adr_id"] for candidate in result["selected_adrs"]}
                self.assertTrue(
                    set(event["gold_adr_ids"]) & selected,
                    f"{case_id} missed all expected ADRs; ranked={[(x['adr_id'],x['score']) for x in result['selected_adrs']]} review={[(x['adr_id'],x['score']) for x in result['review_candidates']]}",
                )

    def test_direct_provider_evidence_creates_only_review_candidate(self):
        event = self.by_id["SCOPE-01"]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        findings = [x for x in result["candidate_assessments"] if x["adr_id"] == "ADR-001"]
        self.assertTrue(findings, "ADR-001 should be retrieved for direct provider-call evidence")
        self.assertEqual(findings[0]["finding_disposition"], "potential_deviation")
        self.assertEqual(result["triage"]["supported_deviation_count"], 0)
        self.assertTrue(findings[0]["source_observations"][0]["excerpt_sha256"])

    def test_no_current_adr_found_is_not_claimed_as_compliance(self):
        event = self.by_id["SCOPE-06"]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        self.assertEqual(result["scope"]["disposition"], "not_in_scope")
        self.assertEqual(result["triage"]["supported_deviation_count"], 0)
        self.assertEqual(result["triage"]["status"], "no_retrieved_adr")


if __name__ == "__main__":
    unittest.main()
