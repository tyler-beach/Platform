#!/usr/bin/env python3
"""Write a safe, versioned manifest for an ADR PoC GitHub Actions run.

Only an explicit allowlist of non-secret workflow inputs is recorded. Artifact
paths and hashes describe output bytes; no source contents, prompts, or secrets
are copied into the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


INPUT_FIELDS = {
    "comparison": "INPUT_COMPARISON",
    "sample_case": "INPUT_SAMPLE_CASE",
    "create_review_issue": "INPUT_CREATE_REVIEW_ISSUE",
    "language": "INPUT_LANGUAGE",
    "source_path": "INPUT_SOURCE_PATH",
    "config_source": "INPUT_CONFIG_SOURCE",
    "root_function": "INPUT_ROOT_FUNCTION",
    "model_provider": "INPUT_MODEL_PROVIDER",
    "adr_path": "INPUT_ADR_PATH",
    "spec_path": "INPUT_SPEC_PATH",
    "diff_path": "INPUT_DIFF_PATH",
    "base_ref": "INPUT_BASE_REF",
    "head_ref": "INPUT_HEAD_REF",
    "max_input_tokens": "INPUT_MAX_INPUT_TOKENS",
    "max_output_tokens": "INPUT_MAX_OUTPUT_TOKENS",
}


def build_manifest(output_path: Path, scan_root: Path | None = None) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    root = (scan_root or output_path.parent).resolve()
    manifest_resolved = output_path.resolve()
    outputs = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.resolve() == manifest_resolved:
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        outputs.append({
            "path": relative,
            "byte_length": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    run = {
        "repository": os.getenv("GITHUB_REPOSITORY", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", ""),
        "run_number": os.getenv("GITHUB_RUN_NUMBER", ""),
        "run_attempt": int(os.getenv("GITHUB_RUN_ATTEMPT", "1") or "1"),
        "run_url": os.getenv("GITHUB_RUN_URL", ""),
        "workflow": os.getenv("GITHUB_WORKFLOW", ""),
        "event": os.getenv("GITHUB_EVENT_NAME", ""),
        "ref": os.getenv("GITHUB_REF", ""),
        "commit": os.getenv("GITHUB_SHA", ""),
        "actor": os.getenv("GITHUB_ACTOR", ""),
    }
    return {
        "schema": "pathfinder.execution-manifest/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": run,
        "inputs": {key: os.getenv(env_name, "") for key, env_name in INPUT_FIELDS.items()},
        "outputs": outputs,
        "output_count": len(outputs),
        "evidence_boundary": (
            "This manifest captures an allowlisted set of workflow parameters and "
            "hashes of generated files. It is execution provenance, not a compliance verdict. "
            "Secret values, source contents, prompts, and provider responses are excluded."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scan-root", type=Path, default=None, help="Root containing generated run outputs to hash")
    args = parser.parse_args()
    manifest = build_manifest(args.output, args.scan_root)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with {manifest['output_count']} hashed output references.")


if __name__ == "__main__":
    main()
