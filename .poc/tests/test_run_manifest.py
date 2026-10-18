from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_manifest import build_manifest


class RunManifestTests(unittest.TestCase):
    def test_allowlisted_inputs_and_hashes_all_outputs_under_scan_root(self):
        with tempfile.TemporaryDirectory() as directory:
            scan_root = Path(directory) / "run-data"
            nested = scan_root / "12345-1"
            nested.mkdir(parents=True)
            evidence_bytes = b'{"finding":"example"}'
            evidence_path = scan_root / "evidence-package.json"
            evidence_path.write_bytes(evidence_bytes)
            manifest_path = nested / "pathfinder-run-manifest.json"
            env = {
                "GITHUB_REPOSITORY": "example/adr-platform",
                "GITHUB_RUN_ID": "12345678901",
                "GITHUB_RUN_ATTEMPT": "2",
                "INPUT_COMPARISON": "spec-vs-implementation",
                "INPUT_MODEL_PROVIDER": "mock",
                "ANTHROPIC_API_KEY": "must-not-appear-in-manifest",
            }
            with patch.dict("os.environ", env, clear=False):
                manifest = build_manifest(manifest_path, scan_root)

            self.assertEqual(manifest["schema"], "pathfinder.execution-manifest/v1")
            self.assertEqual(manifest["run"]["run_attempt"], 2)
            self.assertEqual(manifest["inputs"]["comparison"], "spec-vs-implementation")
            self.assertIn("sample_case", manifest["inputs"])
            self.assertEqual(manifest["inputs"]["model_provider"], "mock")
            self.assertEqual(manifest["output_count"], 1)
            self.assertEqual(manifest["outputs"][0]["path"], "evidence-package.json")
            self.assertEqual(manifest["outputs"][0]["sha256"], hashlib.sha256(evidence_bytes).hexdigest())
            serialized = json.dumps(manifest)
            self.assertNotIn("ANTHROPIC_API_KEY", serialized)
            self.assertNotIn("must-not-appear-in-manifest", serialized)
            self.assertIn("not a compliance verdict", manifest["evidence_boundary"])


if __name__ == "__main__":
    unittest.main()
