from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "requirement_engine"))
import engine
import pdb_collector


DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments
  namespace: apps
spec:
  selector:
    matchLabels:
      app: payments
  template:
    metadata:
      labels:
        app: payments
    spec:
      containers:
        - name: api
          image: example.invalid/payments:1
"""
PDB = """apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: payments-budget
  namespace: apps
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: payments
"""
REQ = {"requirement_id": "ADR-PDB-001", "kind": "resource_present",
       "predicate": "kubernetes.pod_disruption_budget.present", "subject": "apps/payments"}


class PDBCollectorTests(unittest.TestCase):
    def write(self, root: Path, name: str, content: str) -> None:
        (root / name).write_text(content, encoding="utf-8")

    def collect(self, root: Path):
        return pdb_collector.collect_pdb_observation(
            root, workload_name="payments", namespace="apps",
            artifact_id="repo:platform", revision="git:0123456789abcdef",
        )

    def test_matching_pdb_emits_positive_observation_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB)
            evidence = self.collect(root)
            self.assertTrue(evidence["value"])
            self.assertEqual(evidence["locator"]["matching_pdbs"], ["payments-budget"])
            self.assertEqual(len(evidence["source_sha256"]), 64)
            result = engine.evaluate(REQ, [evidence], adr_status="accepted", scope_match=True)
            self.assertEqual(result["outcome"], "no_deviation_found")

    def test_no_matching_pdb_is_negative_only_after_complete_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            evidence = self.collect(root)
            self.assertFalse(evidence["value"])
            self.assertEqual(evidence["locator"]["kind"], "manifest_inventory")
            result = engine.evaluate(REQ, [evidence], adr_status="accepted", scope_match=True)
            self.assertEqual(result["outcome"], "supported_deviation")

    def test_selector_mismatch_is_not_counted_as_pdb_for_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB.replace("app: payments", "app: unrelated"))
            self.assertFalse(self.collect(root)["value"])

    def test_namespace_mismatch_is_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB.replace("namespace: apps", "namespace: other"))
            self.assertFalse(self.collect(root)["value"])

    def test_match_expressions_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            pdb = PDB.replace("matchLabels:\n      app: payments", "matchExpressions:\n      - key: app\n        operator: In\n        values: [payments]")
            self.write(root, "pdb.yaml", pdb)
            self.assertTrue(self.collect(root)["value"])

    def test_null_selector_does_not_select_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB.replace("selector:\n    matchLabels:\n      app: payments", "selector: null"))
            self.assertFalse(self.collect(root)["value"])

    def test_empty_selector_selects_all_in_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB.replace("selector:\n    matchLabels:\n      app: payments", "selector: {}"))
            self.assertTrue(self.collect(root)["value"])

    def test_malformed_yaml_prevents_negative_conclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "broken.yaml", "kind: [not valid")
            with self.assertRaisesRegex(pdb_collector.ManifestError, "cannot safely parse"):
                self.collect(root)

    def test_duplicate_yaml_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "broken.yaml", "apiVersion: v1\nkind: ConfigMap\nkind: Pod\nmetadata:\n  name: x\n")
            with self.assertRaisesRegex(pdb_collector.ManifestError, "duplicate YAML mapping key"):
                self.collect(root)

    def test_missing_workload_is_not_evidence_of_missing_pdb(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "pdb.yaml", PDB)
            with self.assertRaisesRegex(pdb_collector.ManifestError, "was not found"):
                self.collect(root)

    def test_evidence_hash_matches_the_source_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "deployment.yaml", DEPLOYMENT)
            self.write(root, "pdb.yaml", PDB)
            evidence = self.collect(root)
            self.assertEqual(evidence["source_sha256"], hashlib.sha256((root / evidence["path"]).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
