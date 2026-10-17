#!/usr/bin/env python3
"""Export an allowlisted walkthrough from the synthetic mock PoC run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observations import redact_source_text, redact_source_values
from store import SCHEMAS
from functional_analysis_ledger import CONFIDENCE_REASON

SCHEMA_VERSION = "adr-demo-run-v1"
_REPOSITORY_NAME = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}\Z")
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


def _optional_rows(db_dir: Path, table: str) -> list[dict[str, str]]:
    """Read an additive table when present, validating its versioned CSV header."""
    path = db_dir / f"{table}.csv"
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != SCHEMAS[table]:
            raise ValueError(f"CSV schema mismatch in {path}")
        return list(reader)


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
    finding_evidence_ids = _json(finding.get("evidence_ids_json", ""), default=[])
    if not isinstance(finding_evidence_ids, list) or any(not isinstance(value, str) for value in finding_evidence_ids):
        raise ValueError("fixture finding evidence references are malformed")
    known_evidence_ids = {item.get("evidence_id", "") for item in evidence_rows}
    if any(value not in known_evidence_ids for value in finding_evidence_ids):
        raise ValueError("fixture finding evidence reference is missing from exported evidence")
    if finding.get("outcome", "inconclusive") != "inconclusive" and not finding_evidence_ids:
        raise ValueError("fixture finding evidence references are missing")
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
                    "evidence_ids": finding_evidence_ids,
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


def _positive_csv_integer(value: str, field: str) -> int:
    if not isinstance(value, str) or not value.isdecimal() or int(value) <= 0:
        raise ValueError(f"Functional Analysis ledger has invalid {field}")
    return int(value)


def _functional_analysis_records(rows: list[dict[str, str]], repository: str, limit: int) -> list[dict[str, Any]]:
    """Verify and project only the safe record contract written by the reconciler."""
    allowed_states = {"execution_only", "unreconciled", "validated_result"}
    allowed_outcomes = {"", "supported_deviation", "no_deviation_found", "inconclusive"}
    by_identity: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row.get("repository") != repository:
            continue
        workflow_id = _positive_csv_integer(row.get("workflow_id", ""), "workflow ID")
        run_id = _positive_csv_integer(row.get("workflow_run_id", ""), "run ID")
        attempt = _positive_csv_integer(row.get("run_attempt", ""), "run attempt")
        if row.get("record_schema_version") != "1.0.0" or row.get("record_key") != f"{repository}|{workflow_id}|{run_id}|{attempt}":
            raise ValueError("Functional Analysis ledger identity is invalid")
        if not re.fullmatch(r"[a-f0-9]{40}", row.get("workflow_sha", "")):
            raise ValueError("Functional Analysis ledger workflow SHA is invalid")
        if row.get("trigger_event") != "workflow_dispatch" or row.get("execution_status") != "completed":
            raise ValueError("Functional Analysis ledger execution identity is not allowlisted")
        if row.get("persistence_state") not in allowed_states or row.get("domain_outcome", "") not in allowed_outcomes:
            raise ValueError("Functional Analysis ledger state or outcome is invalid")
        if row.get("confidence_status") != "unavailable" or row.get("confidence_reason") != CONFIDENCE_REASON:
            raise ValueError("Functional Analysis ledger confidence must remain explicitly unavailable")
        if row.get("persistence_state") == "validated_result":
            if (row.get("analysis_state") != "validated" or row.get("validation_status") != "passed"
                    or row.get("domain_outcome") not in allowed_outcomes - {""}):
                raise ValueError("validated Functional Analysis row is incomplete")
        elif row.get("domain_outcome") or row.get("validation_status") != "not_run":
            raise ValueError("execution-only Functional Analysis row must not claim an outcome")
        try:
            revision = _positive_csv_integer(row.get("record_revision", ""), "record revision")
        except ValueError:
            raise ValueError("Functional Analysis ledger revision is invalid") from None
        fingerprint = row.get("record_fingerprint", "")
        fingerprint_input = {key: value for key, value in row.items() if key != "record_fingerprint"}
        canonical = json.dumps(fingerprint_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if not re.fullmatch(r"[a-f0-9]{64}", fingerprint) or hashlib.sha256(canonical.encode("utf-8")).hexdigest() != fingerprint:
            raise ValueError("Functional Analysis ledger fingerprint is invalid")
        sources = _json(row.get("source_artifacts_json", ""), default=None)
        evidence = _json(row.get("evidence_refs_json", ""), default=None)
        checks = _json(row.get("validation_checks_json", ""), default=None)
        if not isinstance(sources, list) or not isinstance(evidence, list) or not isinstance(checks, list):
            raise ValueError("Functional Analysis ledger provenance is malformed")
        source_by_id: dict[str, dict[str, str]] = {}
        for source in sources:
            if not isinstance(source, dict) or not re.fullmatch(r"ART-[A-Z0-9-]{1,40}", str(source.get("artifact_id", ""))):
                raise ValueError("Functional Analysis source artifact identity is invalid")
            path = source.get("path")
            digest = source.get("sha256")
            if (source["artifact_id"] in source_by_id or source.get("role") not in {"adr", "implementation", "diff", "technical_spec"}
                    or not isinstance(path, str) or not re.fullmatch(r"input/[A-Za-z0-9_.-]{1,120}", path)
                    or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise ValueError("Functional Analysis source artifact provenance is invalid")
            source_by_id[source["artifact_id"]] = {"artifact_id": source["artifact_id"], "role": source["role"], "path": path, "sha256": digest}
        if len(sources) > 4 or len(evidence) > 500 or len(checks) > 100:
            raise ValueError("Functional Analysis ledger projection exceeds its display limit")
        projected_evidence = []
        seen_evidence: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError("Functional Analysis evidence reference is malformed")
            evidence_id = item.get("evidence_id")
            source = source_by_id.get(item.get("artifact_id"))
            locator = item.get("locator")
            if (not isinstance(evidence_id, str) or not re.fullmatch(r"EV-[A-Z0-9-]{1,48}", evidence_id)
                    or evidence_id in seen_evidence or source is None or item.get("source_path") != source["path"]
                    or item.get("artifact_version") != "sha256:" + source["sha256"]
                    or item.get("evidence_type") not in {"architectural_constraint", "syntax_call_site", "change_diff", "technical_requirement"}
                    or not isinstance(locator, dict)):
                raise ValueError("Functional Analysis evidence reference is invalid")
            start, end = locator.get("line_start"), locator.get("line_end")
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 1 or end < start:
                raise ValueError("Functional Analysis evidence locator is invalid")
            seen_evidence.add(evidence_id)
            projected_evidence.append({"evidence_id": evidence_id, "artifact_id": source["artifact_id"],
                                       "source_sha256": source["sha256"], "source_path": source["path"],
                                       "evidence_type": item["evidence_type"], "line_start": start, "line_end": end})
        projected_checks = []
        for check in checks:
            if (not isinstance(check, dict) or not isinstance(check.get("name"), str)
                    or not re.fullmatch(r"[A-Za-z0-9 ._:-]{1,120}", check["name"])
                    or not isinstance(check.get("passed"), bool)):
                raise ValueError("Functional Analysis validation check is invalid")
            projected_checks.append({"name": check["name"], "passed": check["passed"]})
        by_identity.setdefault(row["record_key"], []).append({**row, "_revision": str(revision),
            "_sources": source_by_id, "_evidence": projected_evidence, "_checks": projected_checks})

    records = []
    for identity, revisions in by_identity.items():
        revisions.sort(key=lambda row: int(row["_revision"]))
        if len({int(row["_revision"]) for row in revisions}) != len(revisions):
            raise ValueError("Functional Analysis ledger has duplicate revisions")
        for previous, current in zip(revisions, revisions[1:]):
            if (int(current["_revision"]) != int(previous["_revision"]) + 1
                    or current.get("supersedes_fingerprint") != previous.get("record_fingerprint")):
                raise ValueError("Functional Analysis ledger revision chain is invalid")
        row = revisions[-1]
        run_id = _positive_csv_integer(row["workflow_run_id"], "run ID")
        attempt = _positive_csv_integer(row["run_attempt"], "run attempt")
        workflow_id = _positive_csv_integer(row["workflow_id"], "workflow ID")
        state = row["persistence_state"]
        conclusion = row["execution_conclusion"]
        if conclusion not in {"success", "failure", "cancelled", "timed_out", "action_required", "skipped", "neutral"}:
            raise ValueError("Functional Analysis execution conclusion is invalid")
        if state == "validated_result":
            status = "complete"
        elif conclusion == "cancelled":
            status = "cancelled"
        elif state == "execution_only":
            status = "failed"
        else:
            status = "unknown"
        artifact_id = _positive_csv_integer(row["actions_artifact_id"], "artifact ID") if row.get("actions_artifact_id") else None
        if state == "validated_result":
            if not artifact_id or row.get("actions_artifact_name") != f"functional-analysis-demo-{run_id}-{attempt}":
                raise ValueError("Functional Analysis Actions artifact reference is invalid")
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", row.get("actions_artifact_digest", "")):
                raise ValueError("Functional Analysis Actions artifact digest is invalid")
        records.append({
            "run_id": row["record_key"], "github_run_id": run_id, "run_attempt": attempt,
            "workflow_url": f"https://github.com/{repository}/actions/runs/{run_id}",
            "started_at": "", "completed_at": "", "comparison": row.get("comparison", ""),
            "language": row.get("language", ""), "provider": "deterministic-mock",
            "outcome": row.get("domain_outcome", ""), "status": status,
            "functional_analysis": {
                "record_key": identity, "record_revision": int(row["_revision"]),
                "execution_status": row["execution_status"], "execution_conclusion": conclusion,
                "analysis_state": row["analysis_state"], "persistence_state": state,
                "persistence_reason": row["persistence_reason"], "domain_outcome": row["domain_outcome"],
                "validation_status": row["validation_status"], "confidence_status": "unavailable",
                "confidence_reason": CONFIDENCE_REASON, "workflow_sha": row["workflow_sha"],
                "comparison_contract": row["comparison_contract"], "sample_case": row["sample_case"],
                "source_artifacts": sorted(row["_sources"].values(), key=lambda item: item["artifact_id"]),
                "evidence_refs": row["_evidence"], "validation_checks": row["_checks"],
                "actions_artifact_id": artifact_id,
                "actions_artifact_name": row.get("actions_artifact_name", ""),
                "actions_artifact_digest": row.get("actions_artifact_digest", ""),
            },
        })
    records.sort(key=lambda item: (item["github_run_id"], item["run_attempt"]), reverse=True)
    return records[:limit]


def build_history_snapshot(db_dir: str | Path, limit: int = 20, actions_history: dict[str, Any] | None = None,
                           repository: str | None = None) -> dict[str, Any]:
    """Project a small, redacted run history from CSV tables; never export raw tables."""
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        raise ValueError("real run history limit must be between 1 and 50")
    history_repository = actions_history.get("repository") if actions_history else None
    repository = repository or history_repository or os.environ.get("GITHUB_REPOSITORY") or "tyler-beach/Platform"
    if not isinstance(repository, str) or not _REPOSITORY_NAME.fullmatch(repository):
        raise ValueError("internal Actions history has an invalid repository name")
    if history_repository is not None and history_repository != repository:
        raise ValueError("internal Actions history repository does not match the configured repository")
    db = Path(db_dir).resolve()
    runs = _rows(db, "runs")
    tables = {
        name: _rows(db, name)
        for name in ("artifacts", "run_events", "evidence", "observations", "collection_reports",
                     "confidence_assessments", "confidence_components", "assessment_evidence_links", "findings")
    }
    functional_rows = _optional_rows(db, "functional_analysis_runs")
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

    projected.extend(_functional_analysis_records(functional_rows, repository, limit))
    projected.sort(key=lambda item: (item.get("github_run_id", 0), item.get("run_attempt", 1)), reverse=True)
    projected = projected[:limit]

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
                            actions_history_path: str | Path | None = None,
                            repository: str | None = None) -> Path:
    path = Path(destination).resolve()
    if path.parent.name != "data" or path.parent.parent.name != "demo" or path.parent.parent.parent.name != "site":
        raise ValueError("real run snapshot output must be under site demo data")
    path.parent.mkdir(parents=True, exist_ok=True)
    actions_history = json.loads(Path(actions_history_path).read_text(encoding="utf-8")) if actions_history_path else None
    snapshot = build_history_snapshot(db_dir, limit, actions_history, repository)
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
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "tyler-beach/Platform"))
    args = parser.parse_args()
    if args.history:
        output = export_history_snapshot(args.db_dir, args.output, args.limit, args.actions_history, args.repository)
        print(f"Exported bounded Pages run history: {output}")
    else:
        if not args.run_dir or not args.fixture_root:
            parser.error("--run-dir and --fixture-root are required for fixture snapshot export")
        output = export_snapshot(args.db_dir, args.run_dir, args.fixture_root, args.output)
        print(f"Exported synthetic Pages walkthrough: {output}")


if __name__ == "__main__":
    main()
