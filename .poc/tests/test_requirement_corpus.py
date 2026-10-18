from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/".poc"/"evaluation"/"requirements"))
import evaluate_requirements as ev

class RequirementCorpusTests(unittest.TestCase):
    def test_six_requirement_types_have_twenty_cases_each(self):
        cases=ev.load_cases()
        self.assertEqual(len(cases),120)
        from collections import Counter
        counts=Counter(c["requirement_type"] for c in cases)
        self.assertEqual(set(counts.values()),{20})
    def test_each_type_has_development_and_locked_holdout_cases(self):
        cases=ev.load_cases()
        for t in {c["requirement_type"] for c in cases}:
            group=[c for c in cases if c["requirement_type"]==t]
            self.assertEqual(sum(c["split"]=="development" for c in group),16)
            self.assertEqual(sum(c["split"]=="locked_holdout" for c in group),4)
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
    def test_fingerprint_is_stable(self):
        self.assertEqual(ev.fingerprint(),ev.fingerprint())
        self.assertEqual(len(ev.fingerprint()),64)
if __name__=="__main__": unittest.main()
