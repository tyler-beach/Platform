from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_manifest import build_manifest


def test_run_manifest_records_allowlisted_inputs_and_hashes_output_files(tmp_path, monkeypatch):
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    evidence_bytes = b'{"finding":"example"}'
    (output_dir / "evidence.json").write_bytes(evidence_bytes)
    manifest_path = output_dir / "pathfinder-run-manifest.json"

    monkeypatch.setenv("GITHUB_REPOSITORY", "example/adr-platform")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345678901")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("INPUT_COMPARISON", "spec-vs-implementation")
    monkeypatch.setenv("INPUT_MODEL_PROVIDER", "mock")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-appear-in-manifest")

    manifest = build_manifest(manifest_path)

    assert manifest["schema"] == "pathfinder.execution-manifest/v1"
    assert manifest["run"]["run_attempt"] == 2
    assert manifest["inputs"]["comparison"] == "spec-vs-implementation"
    assert manifest["inputs"]["model_provider"] == "mock"
    assert manifest["output_count"] == 1
    assert manifest["outputs"][0]["path"] == "evidence.json"
    assert manifest["outputs"][0]["sha256"] == hashlib.sha256(evidence_bytes).hexdigest()
    serialized = json.dumps(manifest)
    assert "ANTHROPIC_API_KEY" not in serialized
    assert "must-not-appear-in-manifest" not in serialized
    assert "not a compliance verdict" in manifest["evidence_boundary"]
