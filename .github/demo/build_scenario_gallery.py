#!/usr/bin/env python3
"""Build a static gallery from the deterministic synthetic workflow fixtures."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".poc" / "demo"))
from functional_analysis_ledger import _json_member, _safe_members, project_bundle

COMPARISONS = ("code-diff", "technical-spec", "spec-vs-implementation")
SAMPLES = ("deviation", "aligned", "insufficient-evidence")
EXPECTED = {
    "deviation": "supported_deviation",
    "aligned": "no_deviation_found",
    "insufficient-evidence": "inconclusive",
}
ALLOWED_ROLES = {"adr", "technical_spec", "implementation", "diff"}
MAX_FIXTURE_BYTES = 32 * 1024
MAX_CATALOG_BYTES = 5 * 1024 * 1024
MAX_LIVE_SCENARIOS = 10
PIPELINE = Path(".github/demo/pipeline.py")
AST_SCAN = Path(".github/demo/ast_scan.py")
LANGUAGE_EXTENSIONS = {"go": ".go", "python": ".py", "javascript": ".js", "typescript": ".ts", "java": ".java"}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("synthetic workflow output must be a JSON object")
    return value


def _run(repository_root: Path, command: list[str], stage: str) -> None:
    result = subprocess.run(command, cwd=repository_root, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"synthetic gallery {stage} stage failed (exit {result.returncode})")


def verify_fixture_artifact(repository_root: Path, artifact: dict[str, Any]) -> Path:
    """Resolve and verify one source strictly under the approved synthetic fixture tree."""
    if not isinstance(artifact, dict) or artifact.get("role") not in ALLOWED_ROLES:
        raise ValueError("artifact role is not allowlisted for the synthetic fixture gallery")
    relative_value = artifact.get("original_fixture_path")
    if not isinstance(relative_value, str):
        raise ValueError("artifact is outside the approved synthetic fixture tree")
    relative = Path(relative_value)
    root = (repository_root / ".github/demo/fixtures").resolve()
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("artifact is outside the approved synthetic fixture tree")
    candidate = repository_root / relative
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("artifact is outside the approved synthetic fixture tree") from exc
    if not candidate.is_file() or candidate.is_symlink() or not resolved.is_file():
        raise ValueError("approved synthetic fixture artifact must be a regular file")
    if resolved.stat().st_size > MAX_FIXTURE_BYTES:
        raise ValueError("synthetic fixture artifact exceeds the per-file size limit")
    raw = resolved.read_bytes()
    expected_hash = artifact.get("sha256")
    if not isinstance(expected_hash, str) or hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("synthetic fixture SHA-256 does not match the pipeline manifest")
    if artifact.get("byte_length") != len(raw):
        raise ValueError("synthetic fixture length does not match the pipeline manifest")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("synthetic fixture source must be UTF-8 text") from exc
    return resolved


def expected_fixture_paths(comparison: str, sample: str, language: str) -> dict[str, str]:
    if comparison not in COMPARISONS or sample not in SAMPLES or language not in LANGUAGE_EXTENSIONS:
        raise ValueError("live artifact scenario selectors are not allowlisted")
    paths = {"adr": ".github/demo/fixtures/adr/ADR-001.md"}
    if comparison in {"code-diff", "spec-vs-implementation"}:
        base = f".github/demo/fixtures/code-diff/{sample}/{language}"
        paths.update({"implementation": base + "/handler" + LANGUAGE_EXTENSIONS[language], "diff": base + "/change.diff"})
    if comparison == "technical-spec":
        paths["technical_spec"] = f".github/demo/fixtures/technical-spec/{sample}.md"
    elif comparison == "spec-vs-implementation":
        paths["technical_spec"] = ".github/demo/fixtures/technical-spec/aligned.md"
    return paths


def project_live_bundle(repository_root: Path, data: bytes, context: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Validate a real Actions bundle and project only its pinned synthetic fixture inputs."""
    if not (Path(repository_root).resolve() / ".github/demo/fixtures").is_dir():
        raise ValueError("approved synthetic fixture tree is missing")
    record = project_bundle(data, context)
    archive, files = _safe_members(data)
    try:
        manifest = _json_member(archive, files, "input-manifest.json")
        report = _json_member(archive, files, "functional-analysis-report.json")
        analysis = _json_member(archive, files, "analysis.json")
        package = _json_member(archive, files, "evidence-package.json")
        candidate_file = _json_member(archive, files, "mock-model-response.json")
        validation = _json_member(archive, files, "validation-result.json")
        budget = _json_member(archive, files, "budget-decision.json")
        comparison, sample, language = manifest["comparison"], manifest["sample_case"], manifest["language"]
        expected_paths = expected_fixture_paths(comparison, sample, language)
        inputs = []
        source_by_id = {}
        for item in manifest["artifacts"]:
            role = item["role"]
            if role not in expected_paths or item.get("original_fixture_path") != expected_paths[role]:
                raise ValueError("live artifact does not use the expected synthetic fixture path")
            raw = archive.read(files[item["path"]])
            if len(raw) > MAX_FIXTURE_BYTES:
                raise ValueError("live synthetic fixture exceeds the Pages input limit")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("live synthetic fixture is not UTF-8 text") from exc
            source_by_id[item["artifact_id"]] = {"role": role, "path": expected_paths[role], "sha256": item["sha256"]}
            inputs.append({"artifact_id": item["artifact_id"], "role": role, "path": expected_paths[role],
                           "sha256": item["sha256"], "byte_length": len(raw), "text": text})
        if {item["role"] for item in inputs} != set(expected_paths):
            raise ValueError("live artifact input roles do not match its selected comparison")
        evidence = []
        for item in package["items"]:
            artifact = source_by_id[item["artifact_id"]]
            locator = item["locator"]
            fact, excerpt = item.get("fact"), item.get("excerpt")
            if not isinstance(fact, str) or len(fact) > 1000 or not isinstance(excerpt, str) or len(excerpt) > 2000:
                raise ValueError("live artifact evidence text exceeds the Pages projection limit")
            evidence.append({"evidence_id": item["evidence_id"], "artifact_id": item["artifact_id"],
                             "role": artifact["role"], "path": artifact["path"],
                             "type": item["evidence_type"], "line_start": locator["line_start"],
                             "line_end": locator["line_end"], "fact": fact, "excerpt": excerpt})
        if len(evidence) > 100:
            raise ValueError("live artifact evidence exceeds the Pages projection limit")
        candidate = candidate_file["candidate"]
        checks = validation["checks"]
        observations = analysis.get("static_analysis", {}).get("observations", [])
        requirements = analysis.get("requirements", [])
        stages = [
            {"id": "admission", "title": "Pin inputs", "status": "passed", "summary": f"{len(inputs)} run inputs pinned by SHA-256."},
            {"id": "analysis", "title": "Analyze sources", "status": "passed", "summary": f"{len(requirements)} requirements and {len(observations)} syntax observations."},
            {"id": "evidence", "title": "Assemble evidence", "status": "passed", "summary": f"{len(evidence)} validated evidence references."},
            {"id": "budget", "title": "Check demo budget", "status": "passed" if budget.get("within_budget") else "failed", "summary": f"{budget.get('estimated_input_tokens', 0)} estimated demo tokens; no provider call."},
            {"id": "mock", "title": "Deterministic mock assessment", "status": "passed", "summary": candidate["outcome"] + " · zero network calls."},
            {"id": "validation", "title": "Validate result", "status": "passed", "summary": f"{len(checks)} bundle validation checks passed."},
        ]
        run_id = context["run_id"]
        attempt = context["run_attempt"]
        return {
            "id": f"live-{run_id}-{attempt}", "record_type": "workflow_run",
            "comparison": comparison, "sample_case": sample, "language": language,
            "outcome": record["domain_outcome"], "rationale": candidate.get("rationale", ""),
            "limitations": candidate.get("limitations", []), "validation_status": "passed",
            "validation_checks": [{"name": item["name"], "passed": True} for item in checks],
            "artifacts": inputs, "evidence": evidence, "stages": stages,
            "observations": [{"line": item.get("line"), "expression": item.get("expression", ""),
                              "classification": item.get("classification", "")} for item in observations[:50]],
            "requirements": [{"line": item.get("line"), "text": item.get("text", ""),
                               "classification": item.get("classification", "")} for item in requirements[:50]],
            "scope_note": analysis.get("static_analysis", {}).get("scope_note", ""),
            "mock_provider": "deterministic-mock", "network_requests": 0,
            "run_id": run_id, "run_attempt": attempt,
            "run_url": f"https://github.com/{context['repository']}/actions/runs/{run_id}",
            "workflow_id": context["workflow_id"], "workflow_sha": context["workflow_sha"],
            "artifact_id": context["artifact_id"], "artifact_name": context["artifact_name"],
            "artifact_sha256": context["artifact_digest"],
            "created_at": str(run.get("created_at") or "")[:40],
            "updated_at": str(run.get("updated_at") or "")[:40],
            "report_status": report["status"],
        }
    finally:
        archive.close()


def eligible_run(run: dict[str, Any], workflow_id: int, default_branch: str) -> bool:
    return (run.get("workflow_id") == workflow_id and run.get("event") == "workflow_dispatch" and
            run.get("head_branch") == default_branch and run.get("status") == "completed" and
            run.get("conclusion") == "success")


def collect_live_scenarios(repository_root: Path, repository: str, token: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from reconcile_functional_analysis import (
        GitHubAPI, ReconciliationError, WORKFLOW_FILE, WORKFLOW_PATH,
        _attempt_context, _list_artifacts, _list_recent_runs,
    )

    api = GitHubAPI(token, repository)
    repo = api.get_json("/")
    default_branch = repo.get("default_branch")
    if repo.get("full_name") != repository or not isinstance(default_branch, str) or not default_branch:
        raise ValueError("GitHub repository identity or default branch could not be verified")
    workflow = api.get_json("/actions/workflows/" + WORKFLOW_FILE)
    workflow_id = workflow.get("id")
    if not isinstance(workflow_id, int) or workflow_id <= 0 or workflow.get("path", "").split("@", 1)[0] != WORKFLOW_PATH:
        raise ValueError("approved Functional Analysis workflow identity could not be verified")
    runs = _list_recent_runs(api, workflow_id)
    candidates = [run for run in runs if eligible_run(run, workflow_id, default_branch)][:MAX_LIVE_SCENARIOS]
    imported: list[dict[str, Any]] = []
    status = {"enabled": True, "eligible_runs": len(candidates), "imported": 0, "rejected": 0, "expired": 0}
    for run in candidates:
        run_id, attempt_number = run.get("id"), run.get("run_attempt")
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0 or not isinstance(attempt_number, int) or attempt_number <= 0 or attempt_number > 20:
            status["rejected"] += 1
            continue
        try:
            attempt = api.get_json(f"/actions/runs/{run_id}/attempts/{attempt_number}")
            if (attempt.get("id") != run_id or attempt.get("run_attempt") != attempt_number or
                    attempt.get("workflow_id") != workflow_id or
                    not eligible_run({**run, **attempt}, workflow_id, default_branch)):
                status["rejected"] += 1
                continue
            context = _attempt_context(repository, default_branch, workflow_id, run, attempt, None)
            if (context.get("execution_status") != "completed" or context.get("execution_conclusion") != "success" or
                    not re.fullmatch(r"[a-fA-F0-9]{40}", str(context.get("workflow_sha", "")))):
                status["rejected"] += 1
                continue
            artifact_name = f"functional-analysis-demo-{run_id}-{attempt_number}"
            matches = [item for item in _list_artifacts(api, run_id) if item.get("name") == artifact_name]
            if len(matches) != 1:
                status["rejected"] += 1
                continue
            artifact = matches[0]
            artifact_run = artifact.get("workflow_run")
            if artifact.get("expired") is True:
                status["expired"] += 1
                continue
            if not isinstance(artifact_run, dict) or artifact_run.get("id") != run_id:
                status["rejected"] += 1
                continue
            context = _attempt_context(repository, default_branch, workflow_id, run, attempt, artifact)
            archive_bytes = api.download_artifact(context["artifact_id"], artifact.get("size_in_bytes"), context["artifact_digest"])
            imported.append(project_live_bundle(repository_root, archive_bytes, context, run))
        except (ValueError, ReconciliationError, KeyError, TypeError):
            status["rejected"] += 1
    status["imported"] = len(imported)
    return imported, status


def _scenario(repository_root: Path, work_root: Path, comparison: str, sample: str) -> dict[str, Any]:
    scenario_id = f"{comparison}--{sample}"
    output = work_root / scenario_id
    python = sys.executable
    base = [python, str(PIPELINE)]
    _run(repository_root, base + ["prepare", "--comparison", comparison, "--sample-case", sample,
                                  "--language", "go", "--run-id", "pages-" + scenario_id,
                                  "--run-attempt", "1", "--output", str(output)], "admission")
    manifest = _json(output / "input-manifest.json")
    artifact_roles = {item.get("role") for item in manifest.get("artifacts", [])}
    if "implementation" in artifact_roles:
        implementation = next(item for item in manifest["artifacts"] if item["role"] == "implementation")
        source_path = output / implementation["path"]
        _run(repository_root, [python, str(AST_SCAN), "--language", "go", "--source", str(source_path),
                              "--out", str(output / "ast-analysis.json")], "Tree-sitter")
    for stage in ("analyze", "evidence", "budget", "mock-model", "validate", "report"):
        _run(repository_root, base + [stage, "--output", str(output)], stage)

    validation = _json(output / "validation-result.json")
    candidate = _json(output / "mock-model-response.json").get("candidate", {})
    analysis = _json(output / "analysis.json")
    evidence_package = _json(output / "evidence-package.json")
    budget = _json(output / "budget-decision.json")
    report = _json(output / "functional-analysis-report.json")
    if validation.get("status") != "passed" or report.get("status") != "passed":
        raise ValueError(f"synthetic scenario {scenario_id} did not pass validation")
    if candidate.get("outcome") != EXPECTED[sample] or report.get("actual_outcome") != EXPECTED[sample]:
        raise ValueError(f"synthetic scenario {scenario_id} did not match its fixture outcome")
    checks = validation.get("checks")
    if not isinstance(checks, list) or not checks or any(not item.get("passed") for item in checks):
        raise ValueError(f"synthetic scenario {scenario_id} contains a failed validation check")
    if len(manifest.get("artifacts", [])) > 4:
        raise ValueError("synthetic scenario has too many input artifacts")

    artifacts = []
    total_input_bytes = 0
    for item in manifest["artifacts"]:
        source = verify_fixture_artifact(repository_root, item)
        raw = source.read_bytes()
        total_input_bytes += len(raw)
        artifacts.append({
            "artifact_id": item["artifact_id"], "role": item["role"],
            "path": item["original_fixture_path"], "sha256": item["sha256"],
            "byte_length": len(raw), "text": raw.decode("utf-8"),
        })
    if total_input_bytes > 4 * MAX_FIXTURE_BYTES:
        raise ValueError("synthetic scenario exceeds the aggregate input size limit")
    artifact_by_id = {item["artifact_id"]: item for item in artifacts}
    evidence = []
    for item in evidence_package.get("items", []):
        artifact = artifact_by_id.get(item.get("artifact_id"))
        locator = item.get("locator", {})
        if not artifact or item.get("artifact_version") != "sha256:" + artifact["sha256"]:
            raise ValueError("synthetic evidence does not resolve to a pinned fixture")
        evidence.append({
            "evidence_id": item["evidence_id"], "artifact_id": item["artifact_id"],
            "role": artifact["role"], "path": artifact["path"],
            "type": item["evidence_type"], "line_start": locator.get("line_start"),
            "line_end": locator.get("line_end"), "fact": item["fact"], "excerpt": item["excerpt"],
        })
    if not evidence or len(evidence) > 100:
        raise ValueError("synthetic evidence count is outside the gallery bounds")

    observations = analysis.get("static_analysis", {}).get("observations", [])
    requirements = analysis.get("requirements", [])
    stages = [
        {"id": "admission", "title": "Pin inputs", "status": "passed", "summary": f"{len(artifacts)} synthetic input files pinned by SHA-256."},
        {"id": "analysis", "title": "Analyze sources", "status": "passed", "summary": f"{len(requirements)} requirements and {len(observations)} syntax observations."},
        {"id": "evidence", "title": "Assemble evidence", "status": "passed", "summary": f"{len(evidence)} version-bound evidence references."},
        {"id": "budget", "title": "Check demo budget", "status": "passed" if budget.get("within_budget") else "failed", "summary": f"{budget.get('estimated_input_tokens', 0)} estimated demo tokens; no provider call."},
        {"id": "mock", "title": "Deterministic mock assessment", "status": "passed", "summary": candidate.get("outcome", "unknown") + " · zero network calls."},
        {"id": "validation", "title": "Validate result", "status": "passed", "summary": f"{len(checks)} validation checks passed."},
    ]
    return {
        "id": scenario_id, "record_type": "curated_fixture", "comparison": comparison, "sample_case": sample,
        "language": "not_applicable" if comparison == "technical-spec" else "go",
        "outcome": candidate["outcome"], "rationale": candidate.get("rationale", ""),
        "limitations": candidate.get("limitations", []), "validation_status": "passed",
        "validation_checks": [{"name": item["name"], "passed": item["passed"]} for item in checks],
        "artifacts": artifacts, "evidence": evidence, "stages": stages,
        "observations": [{"line": item.get("line"), "expression": item.get("expression", ""),
                          "classification": item.get("classification", "")} for item in observations[:50]],
        "requirements": [{"line": item.get("line"), "text": item.get("text", ""),
                           "classification": item.get("classification", "")} for item in requirements[:50]],
        "scope_note": analysis.get("static_analysis", {}).get("scope_note", ""),
        "mock_provider": "deterministic-mock", "network_requests": 0,
    }


def build_gallery(repository_root: Path, live_scenarios: list[dict[str, Any]] | None = None,
                  live_import: dict[str, Any] | None = None,
                  repository: str = "tyler-beach/Platform") -> dict[str, Any]:
    root = Path(repository_root).resolve()
    fixtures = root / ".github/demo/fixtures"
    if not fixtures.is_dir():
        raise ValueError("approved synthetic fixture tree is missing")
    with tempfile.TemporaryDirectory(prefix="adr-synthetic-gallery-") as temporary:
        work_root = Path(temporary)
        scenarios = [
            _scenario(root, work_root, comparison, sample)
            for comparison in COMPARISONS for sample in SAMPLES
        ]
    live_scenarios = live_scenarios or []
    if len(live_scenarios) > MAX_LIVE_SCENARIOS:
        raise ValueError("live scenario count exceeds the gallery limit")
    if len({item.get("id") for item in live_scenarios}) != len(live_scenarios):
        raise ValueError("live scenario identities are duplicated")
    scenarios.extend(live_scenarios)
    catalog = {
        "schema_version": "adr-synthetic-gallery-v1",
        "source": "checked-in synthetic Functional Analysis fixtures",
        "repository": repository,
        "scenario_count": len(scenarios), "live_import": live_import or {
            "enabled": False, "eligible_runs": 0, "imported": 0, "rejected": 0, "expired": 0,
        },
        "scenarios": scenarios,
    }
    encoded = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_CATALOG_BYTES:
        raise ValueError("synthetic scenario catalog exceeds the aggregate size limit")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-live", action="store_true", help="download and validate recent eligible workflow artifacts")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args()
    live_scenarios: list[dict[str, Any]] = []
    live_import: dict[str, Any] | None = None
    if args.include_live:
        live_scenarios, live_import = collect_live_scenarios(
            args.repository_root, args.repository, os.environ.get("GH_TOKEN", ""),
        )
    repository = args.repository or "tyler-beach/Platform"
    catalog = build_gallery(args.repository_root, live_scenarios, live_import, repository)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Validated {catalog['scenario_count']} synthetic scenarios; imported {catalog['live_import']['imported']} live runs ({output.stat().st_size} bytes).")


if __name__ == "__main__":
    main()
