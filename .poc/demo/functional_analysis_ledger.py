"""Validate Functional Analysis bundles and project them into the CSV audit ledger."""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from typing import Any

RECORD_SCHEMA_VERSION = "1.0.0"
CONFIDENCE_REASON = "The deterministic fixture oracle is not confidence; this workflow does not provide validated inputs for the evidence-strength algorithm."
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_EXPANDED_BYTES = 5 * 1024 * 1024
MAX_MEMBER_BYTES = 1024 * 1024
MAX_MEMBERS = 32
MAX_EVIDENCE = 500
MAX_CHECKS = 100
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SAFE_FILE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
_OUTCOMES = {"supported_deviation", "no_deviation_found", "inconclusive"}
_COMPARISONS = {"code-diff", "technical-spec", "spec-vs-implementation"}
_SAMPLES = {"deviation", "aligned", "insufficient-evidence"}
_LANGUAGES = {"go", "python", "javascript", "typescript", "java"}
_ROLES = {"adr", "implementation", "diff", "technical_spec"}
_EVIDENCE_TYPES = {"architectural_constraint", "syntax_call_site", "change_diff", "technical_requirement"}
_ALLOWED_STATIC_MEMBERS = {
    "input-manifest.json", "evidence-package.json", "mock-model-response.json",
    "validation-result.json", "functional-analysis-report.json", "functional-analysis-report.md",
    "analysis.json", "ast-analysis.json", "budget-decision.json",
    "evidence-contract-check.json", "test-oracle.json",
}


def _json_member(archive: zipfile.ZipFile, files: dict[str, zipfile.ZipInfo], name: str) -> dict[str, Any]:
    try:
        value = json.loads(archive.read(files[name]).decode("utf-8"))
    except KeyError as exc:
        raise ValueError(f"required artifact member is missing: {name}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError, OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"artifact member is not valid UTF-8 JSON: {name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"artifact JSON root must be an object: {name}")
    return value


def _safe_members(data: bytes) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("compressed artifact exceeds the allowed size")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("artifact archive is malformed") from exc
    if len(infos) > MAX_MEMBERS:
        archive.close()
        raise ValueError("artifact contains too many members")
    total_size = 0
    files: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = info.filename
        if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
            archive.close()
            raise ValueError("unsafe archive path")
        if name.startswith("/") or any(part in {"", ".", ".."} for part in name.rstrip("/").split("/")):
            archive.close()
            raise ValueError("unsafe archive path")
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            archive.close()
            raise ValueError("symbolic links are not allowed in artifacts")
        if info.is_dir():
            continue
        if name in files:
            archive.close()
            raise ValueError("duplicate archive member")
        if not (name in _ALLOWED_STATIC_MEMBERS or (name.startswith("input/") and _SAFE_FILE.fullmatch(name[6:]))):
            archive.close()
            raise ValueError(f"unknown archive member: {name}")
        if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
            archive.close()
            raise ValueError("artifact member exceeds the allowed size")
        total_size += info.file_size
        if total_size > MAX_EXPANDED_BYTES:
            archive.close()
            raise ValueError("expanded artifact exceeds the allowed size")
        files[name] = info
    return archive, files


def _validate_context(context: dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("workflow run context is malformed")
    repository = context.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", repository):
        raise ValueError("workflow run repository is invalid")
    for field in ("workflow_id", "run_id", "run_attempt", "artifact_id"):
        if not isinstance(context.get(field), int) or isinstance(context.get(field), bool) or context[field] <= 0:
            raise ValueError(f"workflow run {field} is invalid")
    if not isinstance(context.get("workflow_sha"), str) or not re.fullmatch(r"[a-fA-F0-9]{40}", context["workflow_sha"]):
        raise ValueError("workflow source SHA is invalid")
    if context.get("event") != "workflow_dispatch":
        raise ValueError("workflow event is not allowlisted")
    if not isinstance(context.get("default_branch"), str) or not context["default_branch"] or context.get("head_branch") != context["default_branch"]:
        raise ValueError("workflow run is not from the repository default branch")
    if context.get("execution_status") != "completed" or context.get("execution_conclusion") != "success":
        raise ValueError("only successful completed workflow attempts may contain an analysis result")
    expected_name = f"functional-analysis-demo-{context['run_id']}-{context['run_attempt']}"
    if context.get("artifact_name") != expected_name:
        raise ValueError("artifact name does not match the workflow run identity")
    if not isinstance(context.get("artifact_digest"), str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", context["artifact_digest"]):
        raise ValueError("artifact digest is invalid")


def _source_line(raw: bytes, start: int, end: int) -> list[str] | None:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    if start < 1 or end < start or end > len(lines):
        return None
    return lines[start - 1:end]


def _validate_locator(item: dict[str, Any], source: bytes) -> bool:
    locator = item.get("locator")
    excerpt = item.get("excerpt")
    if not isinstance(locator, dict) or not isinstance(excerpt, str) or not excerpt:
        return False
    kind = locator.get("kind")
    start, end = locator.get("line_start"), locator.get("line_end")
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    selected = _source_line(source, start, end)
    if selected is None:
        return False
    if kind == "tree-sitter-node":
        byte_start, byte_end = locator.get("start_byte"), locator.get("end_byte")
        if not isinstance(byte_start, int) or not isinstance(byte_end, int) or byte_start < 0 or byte_end <= byte_start or byte_end > len(source):
            return False
        try:
            return source[byte_start:byte_end].decode("utf-8") == excerpt
        except UnicodeDecodeError:
            return False
    if kind == "diff-line":
        parts = [part.strip() for part in excerpt.split(" | ") if part.strip()]
        available = [line[1:].strip() for line in selected if line.startswith("+") and not line.startswith("+++")]
        return bool(parts) and all(part in available for part in parts)
    if kind == "source-line":
        return any(excerpt.strip() in line for line in selected)
    return False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _record(context: dict[str, Any], values: dict[str, Any]) -> dict[str, str]:
    key = "|".join((context["repository"], str(context["workflow_id"]), str(context["run_id"]), str(context["run_attempt"])))
    record: dict[str, Any] = {
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "record_key": key,
        "record_revision": str(values.get("record_revision", 1)),
        "repository": context["repository"],
        "workflow_id": str(context["workflow_id"]),
        "workflow_sha": context["workflow_sha"].lower(),
        "workflow_run_id": str(context["run_id"]),
        "run_attempt": str(context["run_attempt"]),
        "trigger_event": context.get("event", ""),
        "head_branch": context.get("head_branch", ""),
        "execution_status": context.get("execution_status", ""),
        "execution_conclusion": context.get("execution_conclusion", ""),
        "analysis_state": values.get("analysis_state", "not_started"),
        "persistence_state": values.get("persistence_state", "analysis_result"),
        "persistence_reason": values.get("persistence_reason", ""),
        "domain_outcome": values.get("domain_outcome", ""),
        "validation_status": values.get("validation_status", "not_run"),
        "comparison": values.get("comparison", ""),
        "comparison_contract": values.get("comparison_contract", ""),
        "language": values.get("language", ""),
        "sample_case": values.get("sample_case", ""),
        "evidence_count": str(values.get("evidence_count", 0)),
        "source_artifacts_json": _canonical_json(values.get("source_artifacts", [])),
        "evidence_refs_json": _canonical_json(values.get("evidence_refs", [])),
        "validation_checks_json": _canonical_json(values.get("validation_checks", [])),
        "confidence_status": "unavailable",
        "confidence_algorithm_version": "",
        "confidence_reason": CONFIDENCE_REASON,
        "actions_artifact_id": str(context.get("artifact_id", "")),
        "actions_artifact_name": context.get("artifact_name", ""),
        "actions_artifact_digest": context.get("artifact_digest", ""),
        "supersedes_fingerprint": values.get("supersedes_fingerprint", ""),
    }
    record["record_fingerprint"] = hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()
    return {key: str(value) for key, value in record.items()}


def project_bundle(data: bytes, context: dict[str, Any]) -> dict[str, str]:
    """Validate a final workflow artifact and return its allowlisted ledger row."""
    _validate_context(context)
    archive, files = _safe_members(data)
    try:
        # _safe_members enforces compressed, per-member, and total expanded limits
        # before testzip decompresses any content.
        if archive.testzip() is not None:
            raise ValueError("artifact member checksum validation failed")
        manifest = _json_member(archive, files, "input-manifest.json")
        report = _json_member(archive, files, "functional-analysis-report.json")
        package = _json_member(archive, files, "evidence-package.json")
        candidate_file = _json_member(archive, files, "mock-model-response.json")
        validation = _json_member(archive, files, "validation-result.json")
        if manifest.get("manifest_version") != "1.1.0" or report.get("report_version") != "1.0.0":
            raise ValueError("unsupported artifact schema version")
        if str(manifest.get("run_id")) != str(context["run_id"]) or manifest.get("run_attempt") != context["run_attempt"]:
            raise ValueError("artifact run identity does not match Actions run identity")
        if str(report.get("run_id")) != str(context["run_id"]) or report.get("run_attempt") != context["run_attempt"]:
            raise ValueError("report run identity does not match Actions run identity")
        comparison, sample, language = manifest.get("comparison"), manifest.get("sample_case"), manifest.get("language")
        if comparison not in _COMPARISONS or sample not in _SAMPLES or language not in _LANGUAGES:
            raise ValueError("artifact comparison, sample, or language is not allowlisted")
        expected_contract = {
            "code-diff": "implementation_vs_adr",
            "technical-spec": "technical_spec_vs_adr",
            "spec-vs-implementation": "technical_spec_vs_implementation",
        }[comparison]
        if manifest.get("comparison_contract") != expected_contract or report.get("comparison_contract") != expected_contract:
            raise ValueError("comparison contract does not match the selected comparison")
        raw_artifacts = manifest.get("artifacts")
        if not isinstance(raw_artifacts, list) or not 1 <= len(raw_artifacts) <= 4:
            raise ValueError("manifest artifact list is malformed")
        source_by_id: dict[str, tuple[dict[str, Any], bytes]] = {}
        source_rows = []
        source_roles: set[str] = set()
        source_paths: set[str] = set()
        for item in raw_artifacts:
            if not isinstance(item, dict):
                raise ValueError("manifest source artifact is malformed")
            artifact_id, role, path = item.get("artifact_id"), item.get("role"), item.get("path")
            digest, version, length = item.get("sha256"), item.get("version"), item.get("byte_length")
            if not isinstance(artifact_id, str) or not re.fullmatch(r"ART-[A-Z0-9-]{1,40}", artifact_id) or artifact_id in source_by_id:
                raise ValueError("manifest artifact IDs are invalid or duplicated")
            if role not in _ROLES or role in source_roles:
                raise ValueError("manifest artifact roles are invalid or duplicated")
            if not isinstance(path, str) or not path.startswith("input/") or not _SAFE_FILE.fullmatch(path[6:]) or path in source_paths:
                raise ValueError("manifest source path is invalid or duplicated")
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest) or version != "sha256:" + digest:
                raise ValueError("manifest source hash or version is invalid")
            if not isinstance(length, int) or length < 0:
                raise ValueError("manifest source byte length is invalid")
            try:
                raw = archive.read(files[path])
            except KeyError as exc:
                raise ValueError("manifest source file is missing from artifact bundle") from exc
            if len(raw) != length or hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("pinned source hash does not match artifact bytes")
            source_by_id[artifact_id] = (item, raw)
            source_roles.add(role)
            source_paths.add(path)
            source_rows.append({"artifact_id": artifact_id, "role": role, "path": path, "sha256": digest, "version": version, "byte_length": length})
        expected_roles = {"adr", "implementation", "diff"} if comparison == "code-diff" else ({"adr", "technical_spec"} if comparison == "technical-spec" else {"adr", "implementation", "diff", "technical_spec"})
        if source_roles != expected_roles:
            raise ValueError("manifest source roles do not match selected comparison")
        if package.get("evidence_contract_version") != "1.0.0" or not isinstance(package.get("items"), list):
            raise ValueError("unsupported evidence contract")
        items = package["items"]
        if not 1 <= len(items) <= MAX_EVIDENCE:
            raise ValueError("evidence item count is invalid")
        evidence_by_id: dict[str, dict[str, Any]] = {}
        evidence_refs = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("evidence item is malformed")
            evidence_id, artifact_id = item.get("evidence_id"), item.get("artifact_id")
            if not isinstance(evidence_id, str) or not re.fullmatch(r"EV-[A-Z0-9-]{1,48}", evidence_id) or evidence_id in evidence_by_id:
                raise ValueError("evidence IDs are invalid or duplicated")
            if artifact_id not in source_by_id:
                raise ValueError("evidence references an unknown source artifact")
            source_item, source = source_by_id[artifact_id]
            if item.get("artifact_version") != source_item["version"] or item.get("source_path") != source_item["path"]:
                raise ValueError("evidence source version or path does not match its artifact")
            if item.get("evidence_type") not in _EVIDENCE_TYPES or not _validate_locator(item, source):
                raise ValueError("evidence locator does not resolve to its pinned source bytes")
            evidence_by_id[evidence_id] = item
            locator = item["locator"]
            evidence_refs.append({
                "evidence_id": evidence_id, "artifact_id": artifact_id,
                "artifact_version": source_item["version"], "source_path": source_item["path"],
                "evidence_type": item["evidence_type"],
                "locator": {key: locator[key] for key in ("kind", "line_start", "line_end", "start_byte", "end_byte") if key in locator},
            })
        candidate = candidate_file.get("candidate")
        if not isinstance(candidate, dict) or candidate.get("outcome") not in _OUTCOMES:
            raise ValueError("candidate domain outcome is invalid")
        cited = candidate.get("evidence_ids")
        if not isinstance(cited, list) or not cited or len(cited) != len(set(cited)) or any(ref not in evidence_by_id for ref in cited):
            raise ValueError("candidate evidence references are invalid")
        if candidate_file.get("provider") != "deterministic-mock" or candidate_file.get("network_requests") != 0:
            raise ValueError("Functional Analysis artifact is not from the deterministic offline mock")
        if validation.get("validation_version") != "1.0.0" or validation.get("status") != "passed":
            raise ValueError("analysis validation did not pass")
        checks = validation.get("checks")
        if not isinstance(checks, list) or not 1 <= len(checks) <= MAX_CHECKS:
            raise ValueError("validation check list is malformed")
        check_names: set[str] = set()
        projected_checks = []
        for check in checks:
            if not isinstance(check, dict) or not isinstance(check.get("name"), str) or not check["name"] or not isinstance(check.get("passed"), bool):
                raise ValueError("validation check is malformed")
            if check["name"] in check_names:
                raise ValueError("validation check names are duplicated")
            check_names.add(check["name"])
            if not check["passed"]:
                raise ValueError("analysis validation contains a failed check")
            # Discard untrusted free-form detail strings from the bundle.
            projected_checks.append({"name": check["name"][:120], "passed": True})
        outcome = candidate["outcome"]
        if validation.get("candidate_outcome") != outcome or report.get("actual_outcome") != outcome or report.get("status") != "passed":
            raise ValueError("report, candidate, and validator outcomes do not agree")
        if report.get("evidence_item_count") != len(items):
            raise ValueError("report evidence count does not match evidence package")
        support_types = {evidence_by_id[ref]["evidence_type"] for ref in cited}
        if outcome == "supported_deviation" and not ("architectural_constraint" in support_types and support_types.intersection({"syntax_call_site", "technical_requirement"})):
            raise ValueError("deviation outcome lacks governing and technical evidence")
        if outcome == "no_deviation_found":
            expected = ({"architectural_constraint", "syntax_call_site"} if comparison == "spec-vs-implementation" else {"architectural_constraint", "technical_requirement"})
            if not expected.issubset(support_types):
                raise ValueError("no-deviation outcome lacks comparison evidence")
        if outcome == "inconclusive" and not candidate.get("limitations"):
            raise ValueError("inconclusive outcome lacks a limitation")
        if report.get("comparison") != comparison or report.get("sample_case") != sample or report.get("language") != language:
            raise ValueError("report metadata does not match input manifest")
        return _record(context, {
            "analysis_state": "validated", "persistence_state": "validated_result", "domain_outcome": outcome, "validation_status": "passed",
            "comparison": comparison, "comparison_contract": manifest.get("comparison_contract"),
            "language": language, "sample_case": sample, "evidence_count": len(items),
            "source_artifacts": source_rows, "evidence_refs": evidence_refs,
            "validation_checks": projected_checks,
        })
    finally:
        archive.close()


def execution_only_record(context: dict[str, Any], persistence_state: str = "execution_only") -> dict[str, str]:
    """Project a trusted Actions run with no validated result; never invent an outcome."""
    _validate_context_shape(context)
    if context["execution_conclusion"] == "success" and persistence_state != "unreconciled":
        raise ValueError("a successful run without a validated artifact must be marked unreconciled")
    if context["execution_conclusion"] != "success" and persistence_state != "execution_only":
        raise ValueError("failed execution records must use execution_only persistence state")
    reason = "No validated result artifact was available for this successful run within the reconciliation window." if persistence_state == "unreconciled" else "The workflow ended without a successful analysis result."
    return _record(context, {
        "analysis_state": "unreconciled" if persistence_state == "unreconciled" else "not_started",
        "persistence_state": persistence_state, "persistence_reason": reason,
        "validation_status": "not_run",
    })


def _validate_context_shape(context: dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("workflow run context is malformed")
    if not isinstance(context.get("repository"), str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", context["repository"]):
        raise ValueError("workflow run repository is invalid")
    for field in ("workflow_id", "run_id", "run_attempt"):
        if not isinstance(context.get(field), int) or isinstance(context.get(field), bool) or context[field] <= 0:
            raise ValueError(f"workflow run {field} is invalid")
    if not isinstance(context.get("workflow_sha"), str) or not re.fullmatch(r"[a-fA-F0-9]{40}", context["workflow_sha"]):
        raise ValueError("workflow source SHA is invalid")
    if context.get("event") != "workflow_dispatch" or context.get("head_branch") != context.get("default_branch"):
        raise ValueError("workflow run is not eligible for the default-branch ledger")
    terminal = context.get("execution_status") == "completed"
    failed = context.get("execution_conclusion") in {"failure", "cancelled", "timed_out", "action_required", "skipped", "neutral"}
    unreconciled_success = context.get("execution_conclusion") == "success"
    if not terminal or not (failed or unreconciled_success):
        raise ValueError("execution-only records require a completed attempt without a validated result")


def persist_record(store: Any, record: dict[str, str]) -> str:
    """Append once by composite identity; reject same-key different-content collisions."""
    fingerprint_input = {key: value for key, value in record.items() if key != "record_fingerprint"}
    expected_fingerprint = hashlib.sha256(_canonical_json(fingerprint_input).encode("utf-8")).hexdigest()
    if record.get("record_fingerprint") != expected_fingerprint:
        raise ValueError("functional analysis record fingerprint is invalid")
    rows = [row for row in store.rows("functional_analysis_runs") if row.get("record_key") == record.get("record_key")]
    if len(rows) > 1:
        raise ValueError("duplicate functional analysis ledger identities already exist")
    if rows:
        if any(row.get("record_fingerprint") == record.get("record_fingerprint") for row in rows):
            return "duplicate"
        latest = max(rows, key=lambda row: int(row.get("record_revision") or 1))
        if latest.get("persistence_state") == "unreconciled" and record.get("persistence_state") == "validated_result":
            record = dict(record)
            record["record_revision"] = str(int(latest.get("record_revision") or 1) + 1)
            record["supersedes_fingerprint"] = latest.get("record_fingerprint", "")
            fingerprint_input = {key: value for key, value in record.items() if key != "record_fingerprint"}
            record["record_fingerprint"] = hashlib.sha256(_canonical_json(fingerprint_input).encode("utf-8")).hexdigest()
            store.append("functional_analysis_runs", record)
            return "updated"
        raise ValueError("functional analysis ledger identity collision")
    store.append("functional_analysis_runs", record)
    return "persisted"
