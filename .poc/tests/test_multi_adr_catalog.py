from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "requirement_engine"))

import catalog
import engine
import evaluate_package
import package_collector
import predicate_registry


SAMPLE = ROOT / "requirement_catalog" / "sample_packages" / "multi-domain-session-service" / "package.json"


class MultiAdrCatalogTests(unittest.TestCase):
    def test_catalog_has_one_hundred_approved_requirements(self):
        rows = catalog.load_requirements()
        self.assertEqual(len(rows), 100)
        self.assertTrue(all(row["approval_state"] == "approved" for row in rows))
        self.assertTrue(all(row["label_status"] == "synthetic_unadjudicated" for row in rows))

    def test_registry_loads_catalog_predicates(self):
        predicate_registry.reload()
        caps = predicate_registry.list_capabilities()
        self.assertGreaterEqual(caps["predicate_count"], 100)
        self.assertIn("structured_package", caps["collectors"])

    def test_numeric_min_and_dependency_forbidden_kinds(self):
        digest = "a" * 64
        base = {
            "artifact_id": "a", "revision": "r", "path": "p", "source_sha256": digest,
            "locator": {"kind": "test"},
        }
        min_req = {"requirement_id": "R1", "kind": "numeric_min", "predicate": "kubernetes.deployment.replicas",
                   "subject": "workload", "limit": 3}
        low = {**base, "evidence_id": "E1", "predicate": min_req["predicate"], "subject": "workload", "value": 2}
        self.assertEqual(
            engine.evaluate(min_req, [low], adr_status="accepted", scope_match=True)["outcome"],
            "supported_deviation",
        )
        forbid = {"requirement_id": "R2", "kind": "dependency_forbidden",
                  "predicate": "security.secret_in_source.present", "subject": "repository"}
        hit = {**base, "evidence_id": "E2", "predicate": forbid["predicate"], "subject": "repository", "value": True}
        self.assertEqual(
            engine.evaluate(forbid, [hit], adr_status="accepted", scope_match=True)["outcome"],
            "supported_deviation",
        )

    def test_sample_package_yields_mixed_multi_domain_results(self):
        package = package_collector.load_package(SAMPLE)
        report = evaluate_package.evaluate_package(package)
        self.assertEqual(report["catalog_size"], 100)
        self.assertEqual(report["aggregate_status"], "mixed")
        self.assertGreater(report["counts"]["supported_deviation"], 0)
        self.assertGreater(report["counts"]["no_deviation_found"], 0)
        self.assertGreater(report["counts"]["inconclusive"], 0)
        # Engine never invents a third "partially_aligned" per-requirement outcome.
        for row in report["results"]:
            self.assertIn(row["outcome"], engine.OUTCOMES)

    def test_missing_observation_is_inconclusive_not_aligned(self):
        package = {
            "schema_version": "pathfinder-evidence-package-v1",
            "package_id": "empty-obs",
            "scope": {"domains": ["security"]},
            "observations": [],
        }
        report = evaluate_package.evaluate_package(package)
        security = [row for row in report["results"] if row["domain"] == "security"]
        self.assertTrue(security)
        self.assertTrue(all(row["outcome"] == "inconclusive" for row in security))

    def test_unknown_predicate_in_package_fails_closed(self):
        package = json.loads(SAMPLE.read_text(encoding="utf-8"))
        package["observations"] = [{
            "evidence_id": "EV-BAD",
            "predicate": "not.a.real.predicate",
            "subject": "x",
            "value": True,
            "artifact_id": "tech_spec",
            "revision": "r",
            "path": "p",
            "source_sha256": "a" * 64,
            "locator": {"kind": "test"},
        }]
        with self.assertRaises(Exception):
            package_collector.collect_package_observations(package)


if __name__ == "__main__":
    unittest.main()
