#!/usr/bin/env python3
"""Export an allowlisted walkthrough from the synthetic mock PoC run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observations import redact_source_text, redact_source_values

SCHEMA_VERSION = "adr-demo-run-v1"
STAGE_COPY = {
    "admission": ("Pin inputs", "Record immutable input paths, sizes, and SHA-256 versions."),
    "syntax": ("Parse syntax", "Index syntax and report parser diagnostics."),
    "semantic_analysis": ("Resolve code behavior", "Build symbols, call edges, and entry reachability."),
    "source_collection": ("Collect observations", "Normalize source facts and expose collection coverage."),
    "evidence": ("Assemble evidence", "Link requirement, source, and diff evidence to pinned artifacts."),
    "budget": ("Check model budget", "Estimate input use and record whether a bounded call is allowed."),
    "model": ("Assess and validate", "Use the deterministic mock adapter, then apply evidence and citation gates."),
    "report": ("Write the audit report", "Persist the finding, evidence score, report, and linked CSV rows."),
    "pipeline": ("Pipeline status", "Record the terminal execution state."),
}


def _rows(db_dir: Path, table: str) -> list[dict[str, str]]:
    path = db_dir / f"{table}.csv"
    if not path.is_file():
        raise ValueError(f"missing required run table: {table}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _json(value: str, *, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _require_fixture_artifacts(artifacts: list[dict[str, str]], fixture_root: Path) -> None:
    repo_root = fixture_root.resolve().parents[2]
    expected_fixture = fixture_root.resolve()
    if expected_fixture.name != "go" or expected_fixture.parent.name != "fixtures" or expected_fixture.parent.parent.name != ".poc":
        raise ValueError("approved synthetic fixture root must be .poc/fixtures/go")
    for row in artifacts:
        relative = row.get("path", "")
        if Path(relative).is_absolute():
            raise ValueError("artifact path outside approved synthetic fixture")
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(expected_fixture)
        except ValueError as exc:
            raise ValueError("artifact path outside approved synthetic fixture") from exc


def build_snapshot(db_dir: str | Path, run_dir: str | Path, fixture_root: str | Path) -> dict[str, Any]:
    db = Path(db_dir).resolve()
    run_path = Path(run_dir).resolve()
    fixture = Path(fixture_root).resolve()
    if not run_path.is_dir() or not (run_path / "confidence.json").is_file():
        raise ValueError("run directory is not a completed PoC run")

    runs = _rows(db, "runs")
    run_id = run_path.name
    run_rows = [row for row in runs if row.get("run_id") == run_id]
    if len(run_rows) != 1:
        raise ValueError("expected exactly one indexed run row")
    run = run_rows[0]
    if run.get("model_provider") != "mock":
        raise ValueError("Pages walkthrough only accepts mock-provider runs")

    artifacts = [row for row in _rows(db, "artifacts") if row.get("run_id") == run_id]
    _require_fixture_artifacts(artifacts, fixture)
    artifact_hashes = {row["path"]: row.get("sha256", "") for row in artifacts}

    events = [row for row in _rows(db, "run_events") if row.get("run_id") == run_id]
    ordered_stages: list[str] = []
    stage_rows: dict[str, list[dict[str, str]]] = {}
    for row in events:
        stage = row.get("stage", "")
        if stage and stage not in stage_rows:
            ordered_stages.append(stage)
            stage_rows[stage] = []
        if stage:
            stage_rows[stage].append(row)
    stages = []
    for stage in ordered_stages:
        title, description = STAGE_COPY.get(stage, ("PoC stage", "Recorded workflow stage."))
        rows = stage_rows[stage]
        terminal = next((item for item in reversed(rows) if item.get("status") not in {"running", ""}), rows[-1])
        counts: dict[str, int | bool | str] = {}
        for row in rows:
            details = _json(row.get("details_json", ""), default={})
            if not isinstance(details, dict):
                continue
            # Include count/boolean metadata only; never copy arbitrary event details.
            for key, value in details.items():
                if isinstance(value, bool) or isinstance(value, int) and 0 <= value <= 1_000_000:
                    counts[key] = value
        stages.append({"id": stage, "title": title, "description": description,
                       "status": terminal.get("status", "unknown"), "event_count": len(rows), "counts": counts})

    confidence_path = run_path / "confidence.json"
    confidence = json.loads(confidence_path.read_text(encoding="utf-8"))
    assessment_rows = [row for row in _rows(db, "confidence_assessments") if row.get("run_id") == run_id]
    components = [row for row in _rows(db, "confidence_components") if row.get("run_id") == run_id]
    findings = [row for row in _rows(db, "findings") if row.get("run_id") == run_id]
    evidence_rows = [row for row in _rows(db, "evidence") if row.get("run_id") == run_id]
    observations_rows = [row for row in _rows(db, "observations") if row.get("run_id") == run_id]
    collections = [row for row in _rows(db, "collection_reports") if row.get("run_id") == run_id]
    if len(assessment_rows) != 1 or len(findings) != 1:
        raise ValueError("run is missing its finding or confidence record")

    evidence = []
    for item in evidence_rows:
        path = item.get("path", "")
        if path and path not in artifact_hashes:
            raise ValueError("evidence references a non-fixture artifact")
        evidence.append({
            "id": item.get("evidence_id", ""), "type": item.get("evidence_type", ""),
            "claim": item.get("claim", "")[:500], "excerpt": item.get("excerpt", "")[:1000],
            "path": path, "line": int(item["start_line"]) if item.get("start_line", "").isdigit() else None,
            "source_sha256": artifact_hashes.get(path, ""), "excerpt_sha256": item.get("sha256", ""),
        })

    observations = []
    for item in observations_rows:
        source = _json(item.get("source_ref_json", ""), default={})
        path = source.get("path", "") if isinstance(source, dict) else ""
        if path not in artifact_hashes:
            raise ValueError("observation references a non-fixture artifact")
        observations.append({
            "id": item.get("observation_id", ""), "predicate": item.get("predicate", ""),
            "subject": _json(item.get("subject_json", ""), default={}),
            "value": _json(item.get("value_json", "")), "source_path": path,
            "source_sha256": artifact_hashes[path],
            "locator": source.get("locator", {}), "resolution": _json(item.get("resolution_json", ""), default={}),
            "evidence_class": item.get("evidence_class", ""), "redacted": item.get("redacted") == "True",
        })

    collection_data = []
    for item in collections:
        collection_data.append({
            "source_type": item.get("source_type", ""), "collector": item.get("collector", ""),
            "complete": item.get("complete") == "True", "inspected": int(item.get("inspected_count") or 0),
            "emitted": int(item.get("emitted_count") or 0), "unresolved": int(item.get("unresolved_count") or 0),
            "unsupported_count": len(_json(item.get("unsupported_files_json", ""), default=[])),
            "failed_count": len(_json(item.get("failed_files_json", ""), default=[])),
        })

    assessment = assessment_rows[0]
    if assessment.get("calibrated_probability") not in {"False", "false", "0", ""}:
        raise ValueError("PoC score must not be exported as calibrated probability")
    confidence_data = {
        "score": _number(assessment.get("score_0_to_100")), "band": assessment.get("score_band", "unknown"),
        "algorithm_version": assessment.get("algorithm_version", ""),
        "interpretation": "Evidence-support score; not a calibrated probability.",
        "components": [{
            "dimension": item.get("dimension", ""), "score": _number(item.get("score")),
            "weight": _number(item.get("weight")), "weighted_contribution": _number(item.get("weighted_contribution")),
            "explanation": item.get("explanation", "")[:500],
        } for item in components],
        "caps": confidence.get("caps", []), "guardrails": confidence.get("guardrails", []),
    }

    finding = findings[0]
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "sample": {
            "label": "Synthetic Go fixture · deterministic mock provider", "synthetic": True,
            "provider": "mock", "language": run.get("language", "go"), "comparison": run.get("comparison", ""),
            "outcome": finding.get("outcome", "inconclusive"), "run_status": run.get("status", "unknown"),
            "run_id": run_id, "input_sha256": run.get("input_hash", ""),
            "repository_path": run.get("source_path", ""), "root_function": run.get("root_function", ""),
        },
        "stages": stages,
        "finding": {"outcome": finding.get("outcome", "inconclusive"), "summary": finding.get("summary", "")[:800],
                    "validation_status": finding.get("validation_status", "")},
        "confidence": confidence_data,
        "coverage": collection_data,
        "evidence": evidence,
        "observations": observations,
    }
    # Serialization is also the final guard against accidental non-JSON or object leakage.
    json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    return snapshot


def export_snapshot(db_dir: str | Path, run_dir: str | Path, fixture_root: str | Path, destination: str | Path) -> Path:
    path = Path(destination).resolve()
    if path.parent.name != "data" or path.parent.parent.name != "demo" or path.parent.parent.parent.name != "site":
        raise ValueError("snapshot output must be under site demo data")
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(db_dir, run_dir, fixture_root)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def _safe_relative_path(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("real run ledger contains an unsafe source path")
    return path.as_posix()


def _display_text(value: str, limit: int = 1000) -> tuple[str, bool]:
    safe, changed = redact_source_text(value)
    if len(safe) > limit:
        safe = safe[:limit] + "…"
        changed = True
    return safe, changed


def build_history_snapshot(db_dir: str | Path, limit: int = 20, actions_history: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project a small, redacted run history from CSV tables; never export raw tables."""
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        raise ValueError("real run history limit must be between 1 and 50")
    repository = actions_history.get("repository", "tyler-beach/Platform") if actions_history else "tyler-beach/Platform"
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", repository):
        raise ValueError("internal Actions history has an invalid repository name")
    db = Path(db_dir).resolve()
    runs = _rows(db, "runs")
    tables = {
        name: _rows(db, name)
        for name in ("artifacts", "run_events", "evidence", "observations", "collection_reports",
                     "confidence_assessments", "confidence_components", "assessment_evidence_links", "findings")
    }
    runs.sort(key=lambda row: (row.get("completed_at", ""), row.get("started_at", "")), reverse=True)
    projected = []
    for run in runs[:limit]:
        run_id = run.get("run_id", "")
        artifact_rows = [row for row in tables["artifacts"] if row.get("run_id") == run_id]
        artifact_by_id: dict[str, dict[str, str]] = {}
        artifact_paths: set[str] = set()
        for item in artifact_rows:
            artifact_id = item.get("artifact_id", "")
            if not artifact_id:
                raise ValueError("real run artifact has an empty artifact ID")
            if artifact_id in artifact_by_id:
                raise ValueError("real run has a duplicate artifact ID")
            path = _safe_relative_path(item.get("path", ""))
            if path in artifact_paths:
                raise ValueError("real run has an ambiguous duplicate artifact path")
            digest = item.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("real run artifact has an invalid SHA-256")
            artifact_paths.add(path)
            artifact_by_id[artifact_id] = {"path": path, "sha256": digest}

        run_events = [row for row in tables["run_events"] if row.get("run_id") == run_id]
        stage_order = []
        stage_map: dict[str, list[dict[str, str]]] = {}
        for event in run_events:
            stage = event.get("stage", "")
            if stage and stage not in stage_map:
                stage_order.append(stage); stage_map[stage] = []
            if stage:
                stage_map[stage].append(event)
        stages = []
        for stage in stage_order[:16]:
            title, description = STAGE_COPY.get(stage, ("PoC stage", "Recorded workflow stage."))
            rows = stage_map[stage]
            terminal = next((row for row in reversed(rows) if row.get("status") not in {"running", ""}), rows[-1])
            count_data: dict[str, int | bool] = {}
            for row in rows:
                details = _json(row.get("details_json", ""), default={})
                if isinstance(details, dict):
                    for key, value in details.items():
                        if isinstance(value, bool) or isinstance(value, int) and 0 <= value <= 1_000_000:
                            count_data[key] = value
            stages.append({"id": stage, "title": title, "description": description,
                           "status": terminal.get("status", "unknown"), "event_count": len(rows), "counts": count_data})

        evidence = []
        projected_evidence_ids: set[str] = set()
        for item in tables["evidence"]:
            if item.get("run_id") != run_id:
                continue
            artifact_id = item.get("artifact_id", "")
            artifact = artifact_by_id.get(artifact_id)
            if artifact is None:
                raise ValueError("real run evidence references an unknown artifact ID")
            path = _safe_relative_path(item.get("path", ""))
            if path != artifact["path"]:
                raise ValueError("real run evidence path does not match its artifact ID")
            raw_excerpt = item.get("excerpt", "")
            evidence_id = item.get("evidence_id", "")
            if not evidence_id or evidence_id in projected_evidence_ids:
                raise ValueError("real run evidence has a missing or duplicate evidence ID")
            recorded_hash = item.get("sha256", "")
            if raw_excerpt:
                if not re.fullmatch(r"[0-9a-f]{64}", recorded_hash):
                    raise ValueError("real run evidence has an invalid excerpt SHA-256")
                if hashlib.sha256(raw_excerpt.encode("utf-8")).hexdigest() != recorded_hash:
                    raise ValueError("real run evidence excerpt SHA-256 mismatch")
            elif recorded_hash and not re.fullmatch(r"[0-9a-f]{64}", recorded_hash):
                raise ValueError("real run evidence has an invalid excerpt SHA-256")
            claim, claim_redacted = _display_text(item.get("claim", ""), 500)
            excerpt, excerpt_redacted = _display_text(raw_excerpt, 1000)
            evidence.append({
                "id": evidence_id, "type": item.get("evidence_type", ""),
                "artifact_id": artifact_id, "claim": claim,
                "excerpt": excerpt, "path": path, "line": int(item["start_line"]) if item.get("start_line", "").isdigit() else None,
                "source_sha256": artifact["sha256"], "recorded_excerpt_sha256": recorded_hash,
                "displayed_excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest() if excerpt else "",
                "redacted": claim_redacted or excerpt_redacted,
            })
            projected_evidence_ids.add(evidence_id)
            if len(evidence) >= 200:
                break

        observations = []
        for item in tables["observations"]:
            if item.get("run_id") != run_id:
                continue
            source = _json(item.get("source_ref_json", ""), default={})
            if not isinstance(source, dict):
                raise ValueError("real run observation source reference is malformed")
            artifact_id = source.get("artifact_id", "")
            artifact = artifact_by_id.get(artifact_id)
            if artifact is None:
                raise ValueError("real run observation source reference has an unknown artifact ID")
            path = _safe_relative_path(source.get("path", ""))
            if path != artifact["path"]:
                raise ValueError("real run observation source reference path does not match its artifact ID")
            if source.get("sha256") != artifact["sha256"]:
                raise ValueError("real run observation source reference SHA-256 does not match its artifact ID")
            subject, subject_redacted = redact_source_values(_json(item.get("subject_json", ""), default={}))
            value, value_redacted = redact_source_values(_json(item.get("value_json", "")))
            resolution, resolution_redacted = redact_source_values(_json(item.get("resolution_json", ""), default={}))
            observations.append({
                "id": item.get("observation_id", ""), "artifact_id": artifact_id,
                "predicate": item.get("predicate", ""),
                "subject": subject, "value": value, "source_path": path,
                "source_sha256": artifact["sha256"],
                "locator": source.get("locator", {}) if isinstance(source, dict) else {},
                "resolution": resolution, "evidence_class": item.get("evidence_class", ""),
                "redacted": item.get("redacted") == "True" or subject_redacted or value_redacted or resolution_redacted,
            })
            if len(observations) >= 200:
                break

        confidence_rows = [row for row in tables["confidence_assessments"] if row.get("run_id") == run_id]
        components = []
        for item in tables["confidence_components"]:
            if item.get("run_id") != run_id:
                continue
            explanation, redacted = _display_text(item.get("explanation", ""), 500)
            components.append({"dimension": item.get("dimension", ""), "score": _number(item.get("score")),
                               "weight": _number(item.get("weight")), "weighted_contribution": _number(item.get("weighted_contribution")),
                               "explanation": explanation, "redacted": redacted})
            if len(components) >= 20:
                break
        confidence = None
        if confidence_rows:
            item = confidence_rows[-1]
            if item.get("calibrated_probability") not in {"False", "false", "0", ""}:
                raise ValueError("real run ledger contains a calibrated probability; refuse misleading display")
            confidence = {
                "score": _number(item.get("score_0_to_100")), "band": item.get("score_band", "unknown"),
                "algorithm_version": item.get("algorithm_version", ""),
                "interpretation": "Evidence-support score; not a calibrated probability.", "components": components,
                "caps": _json(item.get("caps_json", ""), default=[]),
                "guardrails": _json(item.get("guardrails_json", ""), default=[]),
            }

        finding_rows = [row for row in tables["findings"] if row.get("run_id") == run_id]
        finding = None
        if finding_rows:
            item = finding_rows[-1]
            evidence_ids = _json(item.get("evidence_ids_json", ""), default=[])
            if not isinstance(evidence_ids, list) or any(not isinstance(value, str) for value in evidence_ids):
                raise ValueError("real run finding evidence references are malformed")
            if item.get("outcome", "inconclusive") != "inconclusive" and not evidence_ids:
                raise ValueError("real run finding evidence references are missing")
            if any(value not in projected_evidence_ids for value in evidence_ids):
                raise ValueError("real run finding evidence reference is not included in the projection")
            summary, summary_redacted = _display_text(item.get("summary", ""), 800)
            rationale, rationale_redacted = _display_text(item.get("rationale", ""), 1200)
            finding = {"outcome": item.get("outcome", "inconclusive"), "summary": summary,
                       "rationale": rationale, "redacted": summary_redacted or rationale_redacted,
                       "validation_status": item.get("validation_status", ""), "evidence_ids": evidence_ids}

        coverage = []
        for item in tables["collection_reports"]:
            if item.get("run_id") != run_id:
                continue
            coverage.append({
                "source_type": item.get("source_type", ""), "collector": item.get("collector", ""),
                "complete": item.get("complete") == "True", "inspected": int(item.get("inspected_count") or 0),
                "emitted": int(item.get("emitted_count") or 0), "unresolved": int(item.get("unresolved_count") or 0),
                "unsupported_count": len(_json(item.get("unsupported_files_json", ""), default=[])),
                "failed_count": len(_json(item.get("failed_files_json", ""), default=[])),
            })

        github_id = run.get("github_run_id", "")
        try:
            github_numeric_id = int(github_id)
            if github_numeric_id <= 0:
                github_numeric_id = 0
        except (TypeError, ValueError):
            github_numeric_id = 0
        workflow_url = f"https://github.com/{repository}/actions/runs/{github_numeric_id}" if github_numeric_id else ""
        projected.append({
            "run_id": run_id, "github_run_id": github_numeric_id,
            "run_attempt": int(run_id.rsplit("-", 1)[1]) if run_id.rsplit("-", 1)[-1].isdigit() else 1,
            "workflow_url": workflow_url, "started_at": run.get("started_at", ""),
            "completed_at": run.get("completed_at", ""), "comparison": run.get("comparison", ""),
            "language": run.get("language", ""), "provider": run.get("model_provider", ""),
            "model": run.get("model", ""), "source_path": _safe_relative_path(run.get("source_path", "")) if run.get("source_path") else "",
            "root_function": run.get("root_function", ""), "input_sha256": run.get("input_hash", ""),
            "outcome": run.get("result", "inconclusive"), "status": run.get("status", "unknown"),
            "stages": stages, "finding": finding, "confidence": confidence,
            "coverage": coverage, "evidence": evidence, "observations": observations,
        })

    api_runs = []
    if actions_history is not None:
        # The collector applies its own API allowlist. Copy only its display contract.
        raw_api_runs = actions_history.get("runs")
        if not isinstance(raw_api_runs, list):
            raise ValueError("internal Actions API snapshot has malformed run history")
        for item in raw_api_runs[:limit]:
            if not isinstance(item, dict):
                continue
            api_runs.append({key: item.get(key) for key in (
                "id", "run_number", "run_attempt", "name", "workflow_file", "workflow_name", "event", "status",
                "conclusion", "head_branch", "head_sha", "created_at", "updated_at", "html_url", "jobs",
            )})
    if actions_history is not None:
        if actions_history.get("schema_version") != "adr-demo-actions-v1" or actions_history.get("available") is not True:
            raise ValueError("internal Actions API snapshot has an unsupported schema")
    result = {"schema_version": "adr-demo-history-v1", "repository": repository,
              "data_available": True,
              "api_history_available": actions_history is not None, "run_count": len(projected),
              "workflow_runs": api_runs, "runs": projected}
    json.dumps(result, ensure_ascii=False, sort_keys=True)
    return result


def export_history_snapshot(db_dir: str | Path, destination: str | Path, limit: int = 20,
                            actions_history_path: str | Path | None = None) -> Path:
    path = Path(destination).resolve()
    if path.parent.name != "data" or path.parent.parent.name != "demo" or path.parent.parent.parent.name != "site":
        raise ValueError("real run snapshot output must be under site demo data")
    path.parent.mkdir(parents=True, exist_ok=True)
    actions_history = json.loads(Path(actions_history_path).read_text(encoding="utf-8")) if actions_history_path else None
    snapshot = build_history_snapshot(db_dir, limit, actions_history)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--run-dir")
    parser.add_argument("--fixture-root")
    parser.add_argument("--output", required=True)
    parser.add_argument("--history", action="store_true", help="export bounded real-run history from the CSV database")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--actions-history")
    args = parser.parse_args()
    if args.history:
        output = export_history_snapshot(args.db_dir, args.output, args.limit, args.actions_history)
        print(f"Exported bounded Pages run history: {output}")
    else:
        if not args.run_dir or not args.fixture_root:
            parser.error("--run-dir and --fixture-root are required for fixture snapshot export")
        output = export_snapshot(args.db_dir, args.run_dir, args.fixture_root, args.output)
        print(f"Exported synthetic Pages walkthrough: {output}")


if __name__ == "__main__":
    main()
