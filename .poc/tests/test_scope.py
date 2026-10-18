from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE_DIR = ROOT / ".poc" / "scope"
sys.path.insert(0, str(SCOPE_DIR))

import retrieval
import run_scope
import index_catalog
import aurora_backend


class ScopeRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = retrieval.load_jsonl(SCOPE_DIR / "adr_catalog.jsonl")
        cls.scenarios = retrieval.load_jsonl(SCOPE_DIR / "scenarios.jsonl")
        cls.by_id = {row["case_id"]: row for row in cls.scenarios}


    def test_catalog_fixture_source_hashes_are_real_and_pinned(self):
        validated = index_catalog.validate_catalog(self.catalog, ROOT)
        self.assertEqual(len(validated), len(self.catalog))
        for row in validated:
            self.assertEqual(len(row["source_sha256"]), 64)
            self.assertTrue((ROOT / row["source_path"]).is_file())

    def test_active_metadata_gate_excludes_retired_adr_even_if_words_match(self):
        event = self.by_id["SCOPE-06"]
        result = retrieval.retrieve(event, self.catalog)
        all_candidates = result["selected_adrs"] + result["review_candidates"]
        self.assertNotIn("ADR-006", {candidate["adr_id"] for candidate in all_candidates})
        excluded = {row["adr_id"]: row for row in result["excluded_adrs"]}
        self.assertIn("ADR-006", excluded)
        self.assertTrue(any("inactive lifecycle" in x for x in excluded["ADR-006"]["reasons"]))
        self.assertNotIn("score", excluded["ADR-006"])
        self.assertNotIn("lifecycle_near_match", excluded["ADR-006"])


    def test_aurora_vector_search_filters_lifecycle_before_similarity_ranking(self):
        sql = aurora_backend.SEARCH_SQL.lower()
        self.assertIn("where status in ('accepted', 'approved', 'active')", sql)
        self.assertIn("review_state in ('current', 'active', 'approved')", sql)
        self.assertIn("effective_until is null or effective_until > now()", sql)
        self.assertNotIn("superseded", sql)
        self.assertNotIn("inactive_search_sql", aurora_backend.__dict__)

    def test_service_and_domain_metadata_gate_is_enforced_before_ranking(self):
        event = dict(self.by_id["SCOPE-01"])
        result = retrieval.retrieve(event, self.catalog)
        candidates = {candidate["adr_id"] for candidate in result["selected_adrs"] + result["review_candidates"]}
        self.assertNotIn("ADR-007", candidates)
        self.assertIn("ADR-001", candidates)

    def test_expected_current_adrs_are_retrieved_for_core_scenarios(self):
        # This is a deliberately small regression corpus; expected retrieval targets
        # are reviewed alongside scenarios.jsonl rather than treated as production stats.
        for case_id in ("SCOPE-01", "SCOPE-02", "SCOPE-03", "SCOPE-04", "SCOPE-05", "SCOPE-08", "SCOPE-10", "SCOPE-11"):
            with self.subTest(case_id=case_id):
                event = self.by_id[case_id]
                result = retrieval.retrieve(event, self.catalog)
                selected = {candidate["adr_id"] for candidate in result["selected_adrs"]}
                self.assertTrue(
                    set(event["gold_adr_ids"]) & selected,
                    f"{case_id} missed all expected ADRs; ranked={[(x['adr_id'],x['score']) for x in result['selected_adrs']]} review={[(x['adr_id'],x['score']) for x in result['review_candidates']]}",
                )


    def test_event_template_returns_an_evidence_linked_comparison(self):
        import json
        event = json.loads((SCOPE_DIR / "event-template.json").read_text(encoding="utf-8"))
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        findings = [x for x in result["adr_matches"] if x["adr_id"] == "ADR-001"]
        self.assertTrue(findings)
        self.assertEqual(findings[0]["comparison_result"], "deviation")
        refs = findings[0]["source_observations"]
        self.assertEqual(refs[0]["evidence_id"], "RUN-123:evidence-0012")
        self.assertEqual(refs[0]["path"], "internal/handler/submit.go")
        self.assertEqual(result["comparison"]["overall_result"], "deviation")

    def test_scope_evaluation_is_deterministic_for_identical_inputs(self):
        import json
        event = self.by_id["SCOPE-01"]
        kwargs = dict(top_k=5, in_scope_threshold=0.28, review_threshold=0.14, backend="local")
        first = run_scope.evaluate_event(event, self.catalog, **kwargs)
        second = run_scope.evaluate_event(event, self.catalog, **kwargs)
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            json.dumps(second, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            "identical event, catalog, thresholds, and backend should replay to the same comparison artifact",
        )

    def test_direct_request_path_call_is_a_deviation_with_typed_evidence_link(self):
        event = self.by_id["SCOPE-01"]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        matches = [x for x in result["adr_matches"] if x["adr_id"] == "ADR-001"]
        self.assertTrue(matches, "ADR-001 should be retrieved for direct provider-call evidence")
        self.assertEqual(matches[0]["comparison_result"], "deviation")
        self.assertEqual(result["comparison"]["overall_result"], "deviation")
        self.assertTrue(matches[0]["requirement_evidence"]["evidence_id"])
        self.assertTrue(matches[0]["source_observations"][0]["excerpt_sha256"])
        links = matches[0]["evidence_links"]
        self.assertTrue(any(link["relationship"] == "contradicts" for link in links))
        self.assertEqual(links[0]["requirement_evidence_id"], matches[0]["requirement_evidence"]["evidence_id"])

    def test_queue_handoff_is_aligned(self):
        result = run_scope.evaluate_event(self.by_id["SCOPE-10"], self.catalog, top_k=5,
                                          in_scope_threshold=0.28, review_threshold=0.14)
        matches = [x for x in result["adr_matches"] if x["adr_id"] == "ADR-001"]
        self.assertTrue(matches)
        self.assertEqual(matches[0]["comparison_result"], "aligned")
        self.assertEqual(matches[0]["evidence_links"][0]["relationship"], "consistent_with")

    def test_worker_provider_call_is_not_mislabeled_as_request_path_deviation(self):
        result = run_scope.evaluate_event(self.by_id["SCOPE-11"], self.catalog, top_k=5,
                                          in_scope_threshold=0.28, review_threshold=0.14)
        matches = [x for x in result["adr_matches"] if x["adr_id"] == "ADR-001"]
        self.assertTrue(matches)
        self.assertEqual(matches[0]["comparison_result"], "aligned")
        self.assertEqual(result["comparison"]["overall_result"], "aligned")

    def test_change_summary_alone_cannot_trigger_deviation(self):
        event = dict(self.by_id["SCOPE-01"])
        event["source_observations"] = [{
            "path": "internal/handler/submit.go", "line": 42,
            "excerpt": "return nil, nil", "caller_qualified_name": "Handler.Submit",
            "evidence_type": "source_observation"
        }]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5,
                                          in_scope_threshold=0.28, review_threshold=0.14)
        match = next(x for x in result["adr_matches"] if x["adr_id"] == "ADR-001")
        self.assertEqual(match["comparison_result"], "uncertain")

    def test_no_current_adr_found_is_not_claimed_as_compliance(self):
        event = self.by_id["SCOPE-09"]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        self.assertEqual(result["scope"]["disposition"], "not_in_scope")
        self.assertEqual(result["comparison"]["overall_result"], "no_applicable_adr")
        self.assertEqual(result["comparison"]["matched_active_adr_count"], 0)

    def test_retired_adr_does_not_match_or_affect_scope_disposition(self):
        event = self.by_id["SCOPE-06"]
        result = run_scope.evaluate_event(event, self.catalog, top_k=5, in_scope_threshold=0.28,
                                          review_threshold=0.14, backend="local")
        self.assertEqual(result["scope"]["disposition"], "not_in_scope")
        self.assertFalse(result["scope"]["selected_adrs"])
        self.assertFalse(result["scope"]["review_candidates"])
        self.assertEqual(result["comparison"]["overall_result"], "no_applicable_adr")
        self.assertEqual(result["comparison"]["matched_active_adr_count"], 0)


if __name__ == "__main__":
    unittest.main()
