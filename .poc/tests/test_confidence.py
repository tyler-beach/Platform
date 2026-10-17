from __future__ import annotations
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import confidence

def evidence(eid, typ, artifact, edge="", text="must enqueue provider assessment asynchronously"):
    return {"evidence_id":eid,"evidence_type":typ,"artifact_id":artifact,"edge_id":edge,"excerpt":text,
            "sha256":hashlib.sha256(text.encode("utf-8")).hexdigest()}

def valid_link():
    return [{"requirement_evidence_id":"EV-REQ","observation_evidence_id":"EV-CALL",
             "relationship":"contradicts","explanation":"Requirement requires async processing; cited call edge reaches the assessment method."}]

class ConfidenceScoringTests(unittest.TestCase):
    def fixture(self):
        ev=[evidence("EV-REQ","normative_requirement","ART-DOC"),
            evidence("EV-CALL","resolved_call_edge","ART-SRC","EDGE-2","return p.Assess(request)")]
        graph={"entry_resolution":"resolved","entry_symbol_ids":["F-SUBMIT"],
          "functions":[
            {"symbol_id":"F-SUBMIT","qualified_name":"Handler.Submit","entry_path_edge_ids":[]},
            {"symbol_id":"F-WORKER","qualified_name":"Worker.Execute","entry_path_edge_ids":["EDGE-1"]},
            {"symbol_id":"F-PROVIDER","qualified_name":"Provider.Assess","entry_path_edge_ids":["EDGE-1","EDGE-2"]}],
          "edges":[
            {"edge_id":"EDGE-1","caller_symbol_id":"F-SUBMIT","callee_symbol_id":"F-WORKER","resolution_status":"resolved","reachable_from_entry":True},
            {"edge_id":"EDGE-2","caller_symbol_id":"F-WORKER","callee_symbol_id":"F-PROVIDER","resolution_status":"resolved","reachable_from_entry":True}],
          "reachable_edges":[
            {"edge_id":"EDGE-1","caller_symbol_id":"F-SUBMIT","callee_symbol_id":"F-WORKER","resolution_status":"resolved"},
            {"edge_id":"EDGE-2","caller_symbol_id":"F-WORKER","callee_symbol_id":"F-PROVIDER","resolution_status":"resolved"}],
          "diagnostics":[]}
        syntax={"files":[{"errors":[]}]}
        artifacts=[{"artifact_id":"ART-DOC","sha256":"doc"},{"artifact_id":"ART-SRC","sha256":"src"}]
        return graph,syntax,ev,artifacts
    def test_transitive_path_gets_explainable_high_score(self):
        graph,syntax,ev,artifacts=self.fixture()
        score=confidence.score_assessment(graph=graph,syntax=syntax,evidence=ev,artifact_rows=artifacts,cited_ids=["EV-REQ","EV-CALL"],evidence_links=valid_link(),proposed_outcome="supported_deviation")
        self.assertEqual(score["accepted_outcome"],"supported_deviation")
        self.assertGreaterEqual(score["score"],0.85)
        self.assertFalse(score["is_calibrated_probability"])
        self.assertEqual({x["dimension"] for x in score["components"]},set(confidence.WEIGHTS))
        self.assertEqual(score["components"][1]["details"]["cited_paths"][0]["path_edge_ids"],["EDGE-1","EDGE-2"])
    def test_missing_requirement_caps_score_and_downgrades(self):
        graph,syntax,ev,artifacts=self.fixture()
        score=confidence.score_assessment(graph=graph,syntax=syntax,evidence=ev,artifact_rows=artifacts,cited_ids=["EV-CALL"],evidence_links=valid_link(),proposed_outcome="supported_deviation")
        self.assertLessEqual(score["score"],0.49)
        self.assertNotEqual(score["accepted_outcome"],"supported_deviation")
        self.assertTrue(score["caps"])
    def test_unknown_citation_caps_score(self):
        graph,syntax,ev,artifacts=self.fixture()
        score=confidence.score_assessment(graph=graph,syntax=syntax,evidence=ev,artifact_rows=artifacts,cited_ids=["EV-REQ","EV-CALL","EV-DOES-NOT-EXIST"],evidence_links=valid_link(),proposed_outcome="supported_deviation")
        self.assertLessEqual(score["score"],0.39)
        self.assertIn("Citation/provenance validation failed: score capped at 0.39.",score["caps"])
    def test_approximate_dispatch_limits_path_score(self):
        graph,syntax,ev,artifacts=self.fixture()
        graph["edges"][1]["resolution_status"]="resolved_approximate"
        graph["reachable_edges"][1]["resolution_status"]="resolved_approximate"
        score=confidence.score_assessment(graph=graph,syntax=syntax,evidence=ev,artifact_rows=artifacts,cited_ids=["EV-REQ","EV-CALL"],evidence_links=valid_link(),proposed_outcome="supported_deviation")
        self.assertLess(score["components"][1]["score"],1.0)
        self.assertIn("resolved_approximate",score["components"][1]["details"]["cited_paths"][0]["edge_statuses"])

    def test_supported_outcome_without_explicit_contradiction_link_is_downgraded(self):
        graph,syntax,ev,artifacts=self.fixture()
        score=confidence.score_assessment(graph=graph,syntax=syntax,evidence=ev,artifact_rows=artifacts,
                                          cited_ids=["EV-REQ","EV-CALL"],evidence_links=[],proposed_outcome="supported_deviation")
        self.assertEqual(score["accepted_outcome"],"potential_deviation")
        self.assertTrue(any("relationship explicitly links" in x for x in score["guardrails"]))

if __name__=="__main__":
    unittest.main()

