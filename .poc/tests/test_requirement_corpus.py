from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/".poc"/"evaluation"/"requirements"))
import evaluate_requirements as ev

class RequirementCorpusTests(unittest.TestCase):
    def test_eight_requirement_types_have_twenty_cases_each(self):
        cases=ev.load_cases()
        self.assertEqual(len(cases),160)
        from collections import Counter
        counts=Counter(c["requirement_type"] for c in cases)
        self.assertEqual(set(counts.values()),{20})
    def test_each_type_has_development_and_locked_holdout_cases(self):
        cases=ev.load_cases()
        for t in {c["requirement_type"] for c in cases}:
            group=[c for c in cases if c["requirement_type"]==t]
            self.assertEqual(sum(c["split"]=="development" for c in group),16)
            self.assertEqual(sum(c["split"]=="locked_holdout" for c in group),4)

    def test_locked_holdout_is_stratified_by_expected_outcome(self):
        cases=ev.load_cases()
        from collections import Counter
        for t in {c["requirement_type"] for c in cases}:
            holdout=Counter(c["gold_label"] for c in cases if c["requirement_type"]==t and c["split"]=="locked_holdout")
            development=Counter(c["gold_label"] for c in cases if c["requirement_type"]==t and c["split"]=="development")
            self.assertEqual(holdout,{"deviation":1,"no_deviation":1,"ambiguous":2})
            self.assertEqual(development,{"deviation":6,"no_deviation":6,"ambiguous":4})
    def test_independent_adjudication_is_not_fabricated(self):
        self.assertTrue(all(c["independent_adjudication_status"]=="pending" for c in ev.load_cases()))
        self.assertEqual(ev.evaluate()["independently_adjudicated_cases"],0)
    def test_evaluator_classifies_all_reference_scenarios(self):
        report=ev.evaluate()
        self.assertEqual(report["total_cases"],120)
        for case in ev.load_cases():
            with self.subTest(case=case["case_id"]):
                self.assertEqual(ev.classify(case),case["gold_label"])
    def test_unknown_or_incomplete_evidence_is_conservative(self):
        cases={c["case_id"]:c for c in ev.load_cases()}
        for cid in ("SESSION-TTL-16","POD-DISRUPTION-BUDGET-15","SENSITIVE-DATA-LOGGING-15","ASYNC-PROVIDER-15","APPROVED-EXCEPTION-15","RUNTIME-EVIDENCE-15"):
            with self.subTest(case=cid):
                self.assertEqual(ev.classify(cases[cid]),"ambiguous")

    def test_observed_sensitive_data_is_a_deviation_even_if_redaction_config_claims_success(self):
        case={"requirement_type":"sensitive_data_logging","facts":{"evidence_complete":True,"sensitive_data_observed":True,"redaction_verified":True}}
        self.assertEqual(ev.classify(case),"deviation")
    def test_conflicting_inline_call_and_async_boundary_is_ambiguous(self):
        case={"requirement_type":"async_provider","facts":{"evidence_complete":True,"dispatch_resolved":True,"direct_sync_call":True,"async_boundary":True}}
        self.assertEqual(ev.classify(case),"ambiguous")
    def test_ttl_exception_requires_verified_validity(self):
        case={"requirement_type":"session_ttl","facts":{"evidence_complete":True,"active_config":True,"ttl_seconds":900,"max_ttl_seconds":600,"exception_valid":None}}
        self.assertEqual(ev.classify(case),"ambiguous")
        case["facts"]["exception_valid"]=True
        self.assertEqual(ev.classify(case),"no_deviation")
        case["facts"]["exception_valid"]=False
        self.assertEqual(ev.classify(case),"deviation")
    def test_encryption_and_least_privilege_domains(self):
        cases={c["case_id"]:c for c in ev.load_cases()}
        self.assertEqual(ev.classify(cases["ENCRYPTION-AT-REST-01"]),"deviation")
        self.assertEqual(ev.classify(cases["ENCRYPTION-AT-REST-07"]),"no_deviation")
        self.assertEqual(ev.classify(cases["ENCRYPTION-AT-REST-19"]),"ambiguous")
        self.assertEqual(ev.classify(cases["LEAST-PRIVILEGE-AUTHORIZATION-01"]),"deviation")
        self.assertEqual(ev.classify(cases["LEAST-PRIVILEGE-AUTHORIZATION-07"]),"no_deviation")
        self.assertEqual(ev.classify(cases["LEAST-PRIVILEGE-AUTHORIZATION-20"]),"ambiguous")

    def test_staging_evidence_cannot_prove_production_state(self):
        for cid in ("ENCRYPTION-AT-REST-20","LEAST-PRIVILEGE-AUTHORIZATION-20"):
            case=next(c for c in ev.load_cases() if c["case_id"]==cid)
            self.assertEqual(ev.classify(case),"ambiguous")

    def test_fingerprint_is_stable(self):
        self.assertEqual(ev.fingerprint(),ev.fingerprint())
        self.assertEqual(len(ev.fingerprint()),64)

    def test_malformed_boolean_values_fail_closed(self):
        cases = [
            {"requirement_type":"session_ttl","facts":{"evidence_complete":"true","active_config":True,"ttl_seconds":900,"max_ttl_seconds":600,"exception_valid":False}},
            {"requirement_type":"pod_disruption_budget","facts":{"evidence_complete":True,"workload_active":"false","pdb_present":True,"pdb_selector_matches":True,"actual_min_available":1,"required_min_available":2}},
            {"requirement_type":"sensitive_data_logging","facts":{"evidence_complete":True,"sensitive_data_observed":"false","redaction_verified":True}},
            {"requirement_type":"async_provider","facts":{"evidence_complete":True,"dispatch_resolved":True,"direct_sync_call":"false","async_boundary":False}},
            {"requirement_type":"approved_exception","facts":{"evidence_complete":True,"exception_used":"false","approved":True,"unexpired":True,"scope_matches":True}},
            {"requirement_type":"runtime_evidence","facts":{"evidence_complete":True,"applicable":True,"evidence_present":"true","fresh":True,"source_pinned":True,"contradicts_requirement":False}},
        ]
        for case in cases:
            with self.subTest(requirement_type=case["requirement_type"]):
                self.assertEqual(ev.classify(case), "ambiguous")

    def test_exception_cannot_be_accepted_when_usage_is_unknown(self):
        case={"requirement_type":"approved_exception","facts":{"evidence_complete":True,"exception_used":None,"approved":True,"unexpired":True,"scope_matches":True}}
        self.assertEqual(ev.classify(case),"ambiguous")

    def test_invalid_numeric_values_are_not_compared(self):
        for value in ("900", True, -1):
            case={"requirement_type":"session_ttl","facts":{"evidence_complete":True,"active_config":True,"ttl_seconds":value,"max_ttl_seconds":600,"exception_valid":False}}
            self.assertEqual(ev.classify(case),"ambiguous")
        case={"requirement_type":"pod_disruption_budget","facts":{"evidence_complete":True,"workload_active":True,"pdb_present":True,"pdb_selector_matches":True,"actual_min_available":-1,"required_min_available":1}}
        self.assertEqual(ev.classify(case),"ambiguous")

    def test_unknown_requirement_type_fails_loudly(self):
        with self.assertRaises(ValueError):
            ev.classify({"requirement_type":"made_up_domain","facts":{"evidence_complete":True}})

if __name__=="__main__": unittest.main()
