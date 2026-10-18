from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "session_ttl"))
import investigate


def artifact(artifact_id: str, revision: str, path: str, content: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "revision": revision,
        "path": path,
        "content": content,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def fixture(ttl: int | None = 720, **overrides) -> dict:
    adr = artifact("ADR-SESSION-001", "git:abc123", "adrs/session-ttl.md", "Session TTL must not exceed 600 seconds.")
    adr["status"] = overrides.pop("adr_status", "accepted")
    source_content = json.dumps({"observations": [] if ttl is None else [{"predicate": "session.ttl_seconds", "value": ttl}]}, separators=(",", ":"))
    source = artifact("service-config", "git:def456", "config/session.json", source_content)
    evidence = []
    if ttl is not None:
        evidence.append({
            "evidence_id": "EV-TTL-1",
            "artifact_id": source["artifact_id"],
            "revision": source["revision"],
            "locator": {"kind": "json_pointer", "value": "/observations/0/value"},
            "predicate": "session.ttl_seconds",
            "value": ttl,
        })
    case = {
        "case_id": "ttl-fixture",
        "adr": adr,
        "source": source,
        "scope_match": True,
        "max_ttl_seconds": 600,
        "evidence": evidence,
    }
    case.update(overrides)
    return case


class SessionTTLInvestigationTests(unittest.TestCase):
    def test_ttl_above_limit_is_supported_deviation(self):
        result = investigate.investigate(fixture(720))
        self.assertEqual(result["outcome"], "supported_deviation")
        self.assertEqual(result["relationship"], "contradicts")
        self.assertIn("EV-TTL-1", result["evidence_ids"])

    def test_ttl_at_limit_is_compliant(self):
        self.assertEqual(investigate.investigate(fixture(600))["outcome"], "no_deviation_found")

    def test_out_of_scope_decision_is_not_applied(self):
        result = investigate.investigate(fixture(720, scope_match=False))
        self.assertFalse(result["applicability"]["applicable"])
        self.assertEqual(result["outcome"], "not_applicable")
        self.assertEqual(result["relationship"], "not_applicable")

    def test_superseded_decision_is_not_applied(self):
        result = investigate.investigate(fixture(720, adr_status="superseded"))
        self.assertFalse(result["applicability"]["applicable"])
        self.assertEqual(result["outcome"], "not_applicable")
        self.assertEqual(result["relationship"], "not_applicable")

    def test_missing_ttl_is_inconclusive(self):
        result = investigate.investigate(fixture(None))
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "insufficient_evidence")

    def test_conflicting_ttl_values_are_inconclusive(self):
        case = fixture(720)
        source_content = json.dumps({"observations": [
            {"predicate": "session.ttl_seconds", "value": 720},
            {"predicate": "session.ttl_seconds", "value": 300},
        ]}, separators=(",", ":"))
        case["source"] = artifact("service-config", "git:def456", "config/session.json", source_content)
        case["evidence"].append({
            "evidence_id": "EV-TTL-2",
            "artifact_id": case["source"]["artifact_id"],
            "revision": case["source"]["revision"],
            "locator": {"kind": "json_pointer", "value": "/observations/1/value"},
            "predicate": "session.ttl_seconds",
            "value": 300,
        })
        result = investigate.investigate(case)
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "conflicting_evidence")

    def test_unknown_model_proposed_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            investigate.investigate(fixture(720, proposed_evidence_ids=["EV-NOT-IN-PACKAGE"]))

    def test_stale_source_revision_is_rejected(self):
        case = fixture(720)
        case["evidence"][0]["revision"] = "git:old-revision"
        with self.assertRaisesRegex(ValueError, "stale artifact revision"):
            investigate.investigate(case)

    def test_evidence_value_must_match_pinned_json_pointer(self):
        case = fixture(720)
        case["evidence"][0]["value"] = 721
        with self.assertRaisesRegex(ValueError, "does not match pinned source locator"):
            investigate.investigate(case)

    def test_json_pointer_rejects_negative_array_index(self):
        case = fixture(720)
        case["evidence"][0]["locator"]["value"] = "/observations/-1/value"
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            investigate.investigate(case)

    def test_json_pointer_rejects_invalid_escape(self):
        case = fixture(720)
        case["evidence"][0]["locator"]["value"] = "/observations/0~2/value"
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            investigate.investigate(case)

    def test_boolean_source_value_cannot_be_relabelled_as_integer_ttl(self):
        case = fixture(1)
        source_content = json.dumps({"observations": [{"predicate": "session.ttl_seconds", "value": True}]}, separators=(",", ":"))
        case["source"] = artifact("service-config", "git:def456", "config/session.json", source_content)
        with self.assertRaisesRegex(ValueError, "does not match pinned source locator"):
            investigate.investigate(case)

    def test_duplicate_proposed_evidence_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be unique"):
            investigate.investigate(fixture(720, proposed_evidence_ids=["EV-TTL-1", "EV-TTL-1"]))

    def test_invalid_policy_limit_is_rejected_even_when_not_applicable(self):
        with self.assertRaisesRegex(ValueError, "max_ttl_seconds"):
            investigate.investigate(fixture(720, scope_match=False, max_ttl_seconds=-1))

    def test_policy_threshold_cannot_be_overridden(self):
        with self.assertRaisesRegex(ValueError, "must equal the 600-second limit"):
            investigate.investigate(fixture(720, max_ttl_seconds=1))

    def test_decision_evidence_excludes_unrelated_package_evidence(self):
        case = fixture(720)
        case["evidence"].append({
            "evidence_id": "EV-ADR-1",
            "artifact_id": case["adr"]["artifact_id"],
            "revision": case["adr"]["revision"],
            "locator": {"kind": "text_span", "value": "1:1-1:40"},
            "predicate": "adr.requirement",
            "value": "Session TTL must not exceed 600 seconds.",
        })
        result = investigate.investigate(case)
        self.assertEqual(result["evidence_ids"], ["EV-TTL-1"])

    def test_non_applicable_result_has_no_decision_evidence(self):
        result = investigate.investigate(fixture(720, scope_match=False))
        self.assertEqual(result["evidence_ids"], [])

    def test_ttl_evidence_rejects_unsupported_locator_kind(self):
        case = fixture(720)
        case["evidence"][0]["locator"] = {"kind": "text_span", "value": "1:1-1:20"}
        with self.assertRaisesRegex(ValueError, "unsupported locator"):
            investigate.investigate(case)

    def test_negative_ttl_observation_is_inconclusive_not_compliant(self):
        case = fixture(-1)
        result = investigate.investigate(case)
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "insufficient_evidence")
        self.assertEqual(result["evidence_ids"], ["EV-TTL-1"])
        self.assertEqual(result["rejected_observations"], [{"evidence_id": "EV-TTL-1", "reason_code": "negative_value"}])

    def test_float_ttl_observation_is_inconclusive_not_compliant(self):
        case = fixture(720)
        source_content = json.dumps({"observations": [{"predicate": "session.ttl_seconds", "value": 12.5}]}, separators=(",", ":"))
        case["source"] = artifact("service-config", "git:def456", "config/session.json", source_content)
        case["evidence"][0]["locator"]["value"] = "/observations/0/value"
        case["evidence"][0]["value"] = 12.5
        result = investigate.investigate(case)
        self.assertEqual(result["outcome"], "inconclusive")
        self.assertEqual(result["relationship"], "insufficient_evidence")
        self.assertEqual(result["evidence_ids"], ["EV-TTL-1"])
        self.assertEqual(result["rejected_observations"], [{"evidence_id": "EV-TTL-1", "reason_code": "unexpected_numeric_type"}])

    def test_mutated_pinned_artifact_hash_is_rejected(self):
        case = fixture(720)
        case["source"]["content"] += " "
        with self.assertRaisesRegex(ValueError, "content hash"):
            investigate.investigate(case)

    def test_non_object_case_is_rejected_with_contract_error(self):
        with self.assertRaisesRegex(ValueError, "case must be a JSON object"):
            investigate.investigate([])

    def test_malformed_evidence_locator_is_rejected_without_attribute_error(self):
        case = fixture(720)
        case["evidence"][0]["locator"] = {"kind": []}
        with self.assertRaisesRegex(ValueError, "requires a typed locator"):
            investigate.investigate(case)

    def test_replay_is_deterministic_for_identical_pinned_inputs(self):
        case = fixture(720)
        first = investigate.investigate(case)
        second = investigate.investigate(case)
        self.assertEqual(first, second)
        self.assertEqual(first["result_sha256"], second["result_sha256"])

    def test_result_hash_changes_when_pinned_input_changes(self):
        first = investigate.investigate(fixture(720))
        second = investigate.investigate(fixture(721))
        self.assertNotEqual(first["result_sha256"], second["result_sha256"])


    def test_result_contract_rejects_unknown_outcome(self):
        result = investigate.investigate(fixture(720))
        result["outcome"] = "probably_compliant"
        with self.assertRaisesRegex(ValueError, "invalid result outcome"):
            investigate.validate_result(result)

    def test_result_contract_rejects_non_applicable_compliance_claim(self):
        result = investigate.investigate(fixture(720))
        result["applicability"]["applicable"] = False
        with self.assertRaisesRegex(ValueError, "non-applicable result"):
            investigate.validate_result(result)

    def test_cli_success_and_repeat_verification(self):
        fixture_path = ROOT / ".poc" / "session_ttl" / "fixtures" / "over-limit.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / ".poc" / "session_ttl" / "investigate.py"),
             str(fixture_path), "--verify-repeat"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["outcome"], "supported_deviation")
        self.assertEqual(parsed["result_sha256"], investigate.investigate(investigate.load_case(fixture_path))["result_sha256"])

    def test_cli_malformed_json_returns_actionable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "bad.json"
            case_path.write_text('{"adr": ', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / ".poc" / "session_ttl" / "investigate.py"), str(case_path)],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_invalid_case_shape_returns_actionable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "array.json"
            case_path.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / ".poc" / "session_ttl" / "investigate.py"), str(case_path)],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("case must be a JSON object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "duplicate.json"
            case_path.write_text('{"case_id":"a","case_id":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                investigate.load_case(case_path)


if __name__ == "__main__":
    unittest.main()
