from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "requirement_engine"))
sys.path.insert(0, str(ROOT / "session_ttl"))

import config_collector
import engine
import investigate
import normalize
import predicate_registry


def obs(value, *, evidence_id="EV-1", predicate="security.encryption_at_rest.enabled", subject="db"):
    return {
        "evidence_id": evidence_id,
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "artifact_id": "repo:platform",
        "revision": "git:abc",
        "path": "config/security.json",
        "source_sha256": hashlib.sha256(b"pinned").hexdigest(),
        "locator": {"kind": "json_pointer", "pointer": "/enabled"},
    }


class SharedEvaluationSpineTests(unittest.TestCase):
    def test_registry_lists_domain_collectors_not_adr_ids(self):
        caps = predicate_registry.list_capabilities()
        self.assertEqual(caps["registry_version"], "predicate-registry-v1")
        self.assertIn("config_json", caps["collectors"])
        self.assertIn("kubernetes_manifest", caps["collectors"])
        self.assertNotIn("ADR-TTL-001", str(caps))

    def test_unknown_predicate_fails_closed(self):
        with self.assertRaises(predicate_registry.CapabilityError):
            predicate_registry.collector_for("made.up.predicate")

    def test_boolean_required_deviation_and_alignment(self):
        requirement = {
            "requirement_id": "ADR-ENC-001",
            "kind": "boolean_required",
            "predicate": "security.encryption_at_rest.enabled",
            "subject": "db",
        }
        aligned = engine.evaluate(requirement, [obs(True)], adr_status="accepted", scope_match=True)
        self.assertEqual(aligned["outcome"], "no_deviation_found")
        deviant = engine.evaluate(requirement, [obs(False)], adr_status="accepted", scope_match=True)
        self.assertEqual(deviant["outcome"], "supported_deviation")

    def test_set_membership_uses_approved_set(self):
        requirement = {
            "requirement_id": "ADR-TLS-001",
            "kind": "set_membership",
            "predicate": "security.tls_policy.id",
            "subject": "edge",
            "approved_set": ["tls-1-2-strict", "tls-1-3-only"],
        }
        ok = engine.evaluate(
            requirement,
            [obs("tls-1-3-only", predicate="security.tls_policy.id", subject="edge")],
            adr_status="accepted",
            scope_match=True,
        )
        self.assertEqual(ok["outcome"], "no_deviation_found")
        bad = engine.evaluate(
            requirement,
            [obs("legacy-ssl", predicate="security.tls_policy.id", subject="edge")],
            adr_status="accepted",
            scope_match=True,
        )
        self.assertEqual(bad["outcome"], "supported_deviation")

    def test_normalizer_requires_approval_before_evaluation(self):
        candidate = {
            "requirement_id": "ADR-TTL-001",
            "kind": "numeric_max",
            "predicate": "session.ttl_seconds",
            "subject": "web-session",
            "limit": 600,
            "adr_id": "ADR-SESSION-001",
            "adr_revision": "git:abc",
            "source_span": {"path": "adrs/session-ttl.md", "excerpt": "must not exceed 600 seconds"},
            "proposal_source": "human",
        }
        proposed = normalize.normalize(candidate, approval_state="proposed")
        self.assertEqual(proposed["approval_state"], "proposed")
        self.assertFalse(proposed["eligible_for_evaluation"])
        with self.assertRaisesRegex(ValueError, "not eligible"):
            normalize.requirement_for_engine(proposed)
        approved = normalize.normalize(candidate, approval_state="approved", approved_by="reviewer@example.com")
        self.assertTrue(approved["eligible_for_evaluation"])
        req = normalize.requirement_for_engine(approved)
        self.assertEqual(req["kind"], "numeric_max")

    def test_normalizer_rejects_unknown_predicate(self):
        candidate = {
            "requirement_id": "ADR-X",
            "kind": "numeric_max",
            "predicate": "not.registered",
            "subject": "x",
            "limit": 1,
            "adr_id": "ADR-X",
            "adr_revision": "git:1",
            "source_span": {"path": "a.md", "excerpt": "x"},
        }
        record = normalize.normalize(candidate, approval_state="proposed")
        self.assertEqual(record["approval_state"], "unnormalized")
        self.assertTrue(any("unknown predicate" in issue for issue in record["validation_issues"]))

    def test_config_collector_emits_registry_predicate(self):
        content = '{"ttl": 720}'
        observation = config_collector.collect_config_observation(
            content=content,
            pointer="/ttl",
            predicate="session.ttl_seconds",
            subject="web-session",
            evidence_id="EV-CFG-1",
            artifact_id="cfg",
            revision="git:1",
            path="session.json",
        )
        self.assertEqual(observation["value"], 720)
        self.assertEqual(observation["collector"], "config_json")
        result = engine.evaluate(
            {
                "requirement_id": "ADR-TTL-001",
                "kind": "numeric_max",
                "predicate": "session.ttl_seconds",
                "subject": "web-session",
                "limit": 600,
            },
            [observation],
            adr_status="accepted",
            scope_match=True,
        )
        self.assertEqual(result["outcome"], "supported_deviation")

    def test_ttl_adapter_uses_shared_engine_numeric_max(self):
        adr = {
            "artifact_id": "ADR-SESSION-001",
            "revision": "git:abc123",
            "path": "adrs/session-ttl.md",
            "content": "Session TTL must not exceed 600 seconds.",
            "sha256": hashlib.sha256(b"Session TTL must not exceed 600 seconds.").hexdigest(),
            "status": "accepted",
        }
        source_content = '{"observations":[{"predicate":"session.ttl_seconds","value":720}]}'
        source = {
            "artifact_id": "service-config",
            "revision": "git:def456",
            "path": "config/session.json",
            "content": source_content,
            "sha256": hashlib.sha256(source_content.encode()).hexdigest(),
        }
        case = {
            "case_id": "ttl-engine-path",
            "adr": adr,
            "source": source,
            "scope_match": True,
            "max_ttl_seconds": 600,
            "evidence": [{
                "evidence_id": "EV-TTL-1",
                "artifact_id": source["artifact_id"],
                "revision": source["revision"],
                "locator": {"kind": "json_pointer", "value": "/observations/0/value"},
                "predicate": "session.ttl_seconds",
                "value": 720,
            }],
        }
        result = investigate.investigate(case)
        self.assertEqual(result["outcome"], "supported_deviation")
        # Prove decision path is the shared engine requirement shape.
        engine_result = engine.evaluate(
            investigate.TTL_REQUIREMENT,
            investigate._engine_observations(
                [{"evidence_id": "EV-TTL-1", "value": 720, "locator": {"kind": "json_pointer", "value": "/observations/0/value"}}],
                source,
            ),
            adr_status="accepted",
            scope_match=True,
        )
        self.assertEqual(engine_result["outcome"], "supported_deviation")
        self.assertEqual(engine_result["requirement"]["kind"], "numeric_max")
        self.assertNotIn("adr_id", engine_result["requirement"])


if __name__ == "__main__":
    unittest.main()
