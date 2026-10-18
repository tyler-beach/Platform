from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "requirement_engine"))
import engine


def observation(value, evidence_id="EV-1", predicate="kubernetes.pod_disruption_budget.present", subject="payments"):
    return {
        "evidence_id": evidence_id,
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "artifact_id": "repo:platform",
        "revision": "git:0123456789abcdef",
        "path": "deploy/k8s/pdb.yaml",
        "source_sha256": hashlib.sha256(b"pinned source fixture").hexdigest(),
        "locator": {"kind": "yaml_resource", "value": "PodDisruptionBudget/payments"},
    }


class GenericRequirementEngineTests(unittest.TestCase):
    def test_pdb_present_is_aligned(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        result = engine.evaluate(requirement, [observation(True)], adr_status="accepted", scope_match=True)
        self.assertEqual(result["outcome"], "no_deviation_found")
        self.assertEqual(result["accepted_evidence_ids"], ["EV-1"])
        self.assertEqual(result["provenance"][0]["path"], "deploy/k8s/pdb.yaml")

    def test_pdb_missing_is_supported_deviation(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        result = engine.evaluate(requirement, [observation(False)], adr_status="accepted", scope_match=True)
        self.assertEqual(result["outcome"], "supported_deviation")
        self.assertEqual(result["relationship"], "contradicts")

    def test_ttl_numeric_max_uses_same_engine(self):
        requirement = {"requirement_id": "ADR-TTL-001", "kind": "numeric_max",
                       "predicate": "session.ttl_seconds", "subject": "web-session", "limit": 600}
        item = observation(601, predicate="session.ttl_seconds", subject="web-session")
        result = engine.evaluate(requirement, [item], adr_status="accepted", scope_match=True)
        self.assertEqual(result["outcome"], "supported_deviation")

    def test_no_matching_observation_is_inconclusive(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        result = engine.evaluate(requirement, [], adr_status="accepted", scope_match=True)
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "insufficient_evidence")

    def test_conflicting_observations_are_inconclusive(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        result = engine.evaluate(requirement, [observation(True), observation(False, "EV-2")],
                                 adr_status="accepted", scope_match=True)
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "conflicting_evidence")

    def test_out_of_scope_is_not_applicable_without_evidence_claim(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        result = engine.evaluate(requirement, [observation(False)], adr_status="accepted", scope_match=False)
        self.assertEqual(result["outcome"], "not_applicable")
        self.assertEqual(result["considered_evidence_ids"], [])

    def test_duplicate_evidence_ids_are_rejected(self):
        requirement = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
                       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "payments"}
        with self.assertRaisesRegex(ValueError, "unique"):
            engine.evaluate(requirement, [observation(True), observation(False)], adr_status="accepted", scope_match=True)

    def test_numeric_boolean_is_not_accepted_as_number(self):
        requirement = {"requirement_id": "ADR-TTL-001", "kind": "numeric_max",
                       "predicate": "session.ttl_seconds", "subject": "web-session", "limit": 600}
        with self.assertRaisesRegex(ValueError, "invalid value type"):
            engine.evaluate(requirement, [observation(True, predicate="session.ttl_seconds", subject="web-session")],
                            adr_status="accepted", scope_match=True)

if __name__ == "__main__":
    unittest.main()
