from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc"))

import observations


class ObservationContractTests(unittest.TestCase):
    def test_call_edges_normalize_to_language_neutral_observations(self):
        graph = {
            "language": "go",
            "resolver": "go-ssa-cha-v1",
            "edges": [{
                "edge_id": "run-1:edge-1",
                "caller_symbol_id": "run-1:Submit",
                "callee_symbol_id": "run-1:Provider.Assess",
                "caller_qualified_name": "Handler.Submit",
                "callee_qualified_name": "Provider.Assess",
                "call_expression": "h.Provider.Assess(ctx, req)",
                "path": "handler.go",
                "line": 42,
                "resolution_status": "resolved_static",
                "resolution_basis": "go/types",
                "reachable_from_entry": True,
            }],
        }
        artifact = {"artifact_id": "run-1:artifact-1", "version": "sha256:" + "a" * 64,
                    "sha256": "a" * 64}
        result = observations.from_callgraph(graph, {"handler.go": artifact}, run_id="run-1")

        self.assertEqual(len(result["observations"]), 1)
        item = result["observations"][0]
        self.assertEqual(item["predicate"], "code.call_edge")
        self.assertEqual(item["value"]["target"], "Provider.Assess")
        self.assertEqual(item["source_ref"]["artifact_id"], artifact["artifact_id"])
        self.assertEqual(item["source_ref"]["locator"], {"kind": "line", "start": 42, "end": 42})
        self.assertEqual(item["collector"]["language"], "go")
        self.assertTrue(result["coverage"]["complete"])

    def test_yaml_and_json_emit_generic_properties_with_source_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pdb.yaml").write_text(
                "apiVersion: policy/v1\nkind: PodDisruptionBudget\nmetadata:\n  name: payments\n  namespace: production\nspec:\n  minAvailable: 2\n  selector:\n    matchLabels:\n      app: payments\n",
                encoding="utf-8",
            )
            (root / "auth.json").write_text(
                '{\n  "auth": {"maxTokenLifetimeSeconds": 3600}\n}\n', encoding="utf-8"
            )
            artifacts = {
                "pdb.yaml": {"artifact_id": "a-pdb", "version": "sha256:" + "b" * 64, "sha256": "b" * 64},
                "auth.json": {"artifact_id": "a-auth", "version": "sha256:" + "c" * 64, "sha256": "c" * 64},
            }
            result = observations.collect_configuration(root, artifacts)

        items = result["observations"]
        pdb = next(x for x in items if x["source_ref"]["path"] == "pdb.yaml" and x["value"] == 2)
        ttl = next(x for x in items if x["source_ref"]["path"] == "auth.json")
        self.assertEqual(pdb["predicate"], "configuration.property")
        self.assertEqual(pdb["subject"]["kind"], "PodDisruptionBudget")
        self.assertEqual(pdb["source_ref"]["locator"]["kind"], "yaml_path")
        self.assertEqual(pdb["source_ref"]["locator"]["line"], 7)
        self.assertEqual(pdb["source_ref"]["artifact_id"], "a-pdb")
        self.assertEqual(ttl["source_ref"]["locator"]["pointer"], "/auth/maxTokenLifetimeSeconds")
        self.assertEqual(ttl["value"], 3600)
        self.assertTrue(result["coverage"]["complete"])

    def test_secret_values_are_redacted_but_token_lifetime_settings_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake_access_key = "AKIA" + "ABCDEFGHIJKLMNOP"
            (root / "settings.yaml").write_text(
                "auth:\n  maxTokenLifetimeSeconds: 3600\n  apiToken: do-not-leak\n"
                f"  accessKeyId: {fake_access_key}\n"
                "---\napiVersion: v1\nkind: Secret\nmetadata:\n  name: api\nstringData:\n  token: another-secret\n",
                encoding="utf-8",
            )
            digest = "d" * 64
            result = observations.collect_configuration(
                root, {"settings.yaml": {"artifact_id": "a1", "version": "sha256:" + digest, "sha256": digest}}
            )

        serialized = json.dumps(result["observations"], sort_keys=True)
        self.assertNotIn("do-not-leak", serialized)
        self.assertNotIn(fake_access_key, serialized)
        self.assertNotIn("another-secret", serialized)
        self.assertTrue(any(x["value"] == 3600 for x in result["observations"]))
        redacted = [x for x in result["observations"] if x.get("redacted")]
        self.assertGreaterEqual(len(redacted), 2)
        self.assertGreaterEqual(result["coverage"]["redacted_value_count"], 2)

    def test_parse_failure_and_unsupported_config_files_make_coverage_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bad.yaml").write_text("broken: [unterminated\n", encoding="utf-8")
            (root / "main.tf").write_text('resource "aws_s3_bucket" "data" {}\n', encoding="utf-8")
            result = observations.collect_configuration(root, {})

        self.assertFalse(result["coverage"]["complete"])
        self.assertEqual(result["coverage"]["failed_files"], ["bad.yaml"])
        self.assertEqual(result["coverage"]["unsupported_files"], ["main.tf"])
        self.assertFalse(result["observations"])

    def test_duplicate_yaml_keys_are_not_emitted_as_ambiguous_facts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "duplicate.yaml").write_text("spec:\n  replicas: 2\n  replicas: 5\n", encoding="utf-8")
            digest = "f" * 64
            result = observations.collect_configuration(
                root, {"duplicate.yaml": {"artifact_id": "a1", "version": "sha256:" + digest, "sha256": digest}}
            )
        self.assertFalse(result["coverage"]["complete"])
        self.assertFalse(result["observations"])
        self.assertEqual(result["coverage"]["diagnostics"][0]["error_code"], "duplicate_mapping_key")

    def test_parser_diagnostics_do_not_echo_source_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "bad.yaml").write_text("setting: CANARY-PRIVATE-VALUE\nbroken: [\n", encoding="utf-8")
            digest = "9" * 64
            result = observations.collect_configuration(
                root, {"bad.yaml": {"artifact_id": "a1", "version": "sha256:" + digest, "sha256": digest}}
            )
        self.assertFalse(result["coverage"]["complete"])
        self.assertNotIn("CANARY-PRIVATE-VALUE", json.dumps(result["coverage"]))

    def test_source_excerpt_redacts_quoted_literals_without_losing_call_shape(self):
        excerpt = 'return provider.assess("CANARY-CODE-SECRET")'
        redacted, changed = observations.redact_source_text(excerpt)
        self.assertTrue(changed)
        self.assertNotIn("CANARY-CODE-SECRET", redacted)
        self.assertIn("provider.assess", redacted)

    def test_entropy_redaction_finds_opaque_tokens_without_redacting_symbol_syntax(self):
        secret = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
        surrounding = f"credential candidate {secret} was found"
        redacted, changed = observations.redact_source_text(surrounding)
        self.assertTrue(changed)
        self.assertNotIn(secret, redacted)
        self.assertIn("credential candidate", redacted)
        self.assertIn("was found", redacted)

        digest = "a" * 64
        preserved_digest, digest_changed = observations.redact_source_text(digest)
        self.assertEqual(preserved_digest, digest)
        self.assertFalse(digest_changed)

    def test_long_qualified_callgraph_symbols_keep_exact_provenance(self):
        caller = "(*example.com/adr-poc.HttpHandler).SubmitRequest"
        callee = "(*example.com/adr-poc.AssessmentProvider).AssessRequest"
        graph = {
            "language": "go", "resolver": "go-ssa-cha-v1",
            "edges": [{
                "edge_id": "run-1:edge-1", "caller_symbol_id": "run-1:caller", "callee_symbol_id": "run-1:callee",
                "caller_qualified_name": caller, "callee_qualified_name": callee,
                "call_expression": "h.Provider.AssessRequest(ctx, req)", "path": "handler.go", "line": 42,
                "resolution_status": "resolved_approximate", "resolution_basis": "go_types_cha_interface_dispatch",
                "reachable_from_entry": True,
            }],
        }
        digest = "a" * 64
        artifact = {"artifact_id": "run-1:artifact-1", "version": "sha256:" + digest, "sha256": digest}
        result = observations.from_callgraph(graph, {"handler.go": artifact}, run_id="run-1")
        item = result["observations"][0]
        self.assertEqual(item["subject"]["name"], caller)
        self.assertEqual(item["value"]["target"], callee)
        self.assertEqual(item["source_ref"]["sha256"], digest)
        self.assertEqual(item["source_ref"]["locator"], {"kind": "line", "start": 42, "end": 42})

    def test_credential_shaped_source_line_is_redacted_as_a_whole(self):
        excerpt = 'headers["Authorization"] = "Bearer CANARY-BEARER-TOKEN"'
        redacted, changed = observations.redact_source_text(excerpt)
        self.assertTrue(changed)
        self.assertNotIn("CANARY-BEARER-TOKEN", redacted)

    def test_invalid_or_unpinned_observation_is_rejected(self):
        invalid = {
            "schema_version": observations.SCHEMA_VERSION,
            "observation_id": "obs-1", "predicate": "configuration.property", "value": "on",
            "subject": {"id": "cfg:/config"},
            "source_ref": {"path": "config.yaml", "version": "current", "sha256": "a" * 64,
                           "locator": {"kind": "yaml_path", "path": ["on"]}},
            "collector": {"version": "adapter-v1"}, "resolution": {"status": "direct"},
            "evidence_class": "declared_configuration",
        }
        with self.assertRaisesRegex(ValueError, "artifact_id"):
            observations.validate_observation(invalid)

    def test_observation_ids_are_stable_for_same_pinned_fact(self):
        fact = {
            "run_id": "run-1", "predicate": "configuration.property", "subject": {"id": "cfg:/a"},
            "value": 3, "source_ref": {"artifact_id": "artifact-1", "version": "sha256:" + "e" * 64,
                           "path": "config.yaml", "locator": {"kind": "yaml_path", "path": ["spec", "replicas"], "line": 9}},
        }
        self.assertEqual(observations.observation_id(fact), observations.observation_id(fact))
        changed = {**fact, "value": 4}
        self.assertNotEqual(observations.observation_id(fact), observations.observation_id(changed))


if __name__ == "__main__":
    unittest.main()
