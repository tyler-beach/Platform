from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "requirement_engine"))
import evaluate_pdb


DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout
  namespace: production
spec:
  selector:
    matchLabels:
      app: checkout
  template:
    metadata:
      labels:
        app: checkout
    spec:
      containers:
        - name: checkout
          image: example.invalid/checkout:1
"""
PDB = """apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: checkout-budget
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: checkout
"""


class PDBVerticalSliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "deployment.yaml").write_text(DEPLOYMENT, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self, **kwargs):
        return evaluate_pdb.evaluate_pdb(
            self.root,
            workload_name="checkout",
            namespace="production",
            revision="git:0123456789abcdef",
            artifact_id="fixture-repo",
            **kwargs,
        )

    def test_matching_pdb_is_aligned_with_inspectable_provenance(self):
        (self.root / "pdb.yaml").write_text(PDB, encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["outcome"], "no_deviation_found")
        self.assertEqual(result["accepted_evidence_ids"], [
            "PDB:production/checkout:git:0123456789abcdef"
        ])
        self.assertEqual(result["provenance"][0]["path"], "pdb.yaml")
        self.assertEqual(len(result["provenance"][0]["source_sha256"]), 64)
        self.assertEqual(result["provenance"][0]["locator"]["kind"], "yaml_resource")
        self.assertEqual(len(result["result_sha256"]), 64)

    def test_missing_matching_pdb_is_supported_deviation(self):
        result = self.evaluate()
        self.assertEqual(result["outcome"], "supported_deviation")
        self.assertEqual(result["relationship"], "contradicts")
        self.assertEqual(result["provenance"][0]["path"], "deployment.yaml")
        self.assertEqual(result["provenance"][0]["locator"]["kind"], "manifest_inventory")
        self.assertEqual(result["provenance"][0]["locator"]["matching_pdbs"], [])

    def test_out_of_scope_is_not_applicable_and_does_not_collect_evidence(self):
        result = self.evaluate(scope_match=False)
        self.assertEqual(result["outcome"], "not_applicable")
        self.assertEqual(result["considered_evidence_ids"], [])
        self.assertEqual(result["provenance"], [])

    def test_malformed_inventory_is_inconclusive_not_a_deviation(self):
        (self.root / "broken.yaml").write_text("kind: [broken", encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "insufficient_evidence")
        self.assertEqual(result["uncertainty"], ["collection_failed"])
        self.assertEqual(result["accepted_evidence_ids"], [])
        self.assertEqual(result["evidence_gap"]["code"], "manifest_collection_failed")

    def test_missing_workload_is_inconclusive_not_missing_pdb(self):
        (self.root / "deployment.yaml").unlink()
        (self.root / "pdb.yaml").write_text(PDB, encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["accepted_evidence_ids"], [])

    def test_result_fingerprint_is_stable_for_identical_input(self):
        (self.root / "pdb.yaml").write_text(PDB, encoding="utf-8")
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first["result_sha256"], second["result_sha256"])


if __name__ == "__main__":
    unittest.main()
