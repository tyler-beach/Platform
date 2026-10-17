"""Source-neutral, provenance-bound observations for the ADR PoC.

Parsers are adapters: their syntax and resolution details stay in collector
metadata while assessments consume a common observation envelope.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

SCHEMA_VERSION = "source-observation-v1"
CODE_COLLECTOR_VERSION = "callgraph-observations-v1"
CONFIG_COLLECTOR_VERSION = "structured-config-observations-v1"
CONFIG_SUFFIXES = {".yaml", ".yml", ".json"}
RECOGNIZED_UNSUPPORTED_SUFFIXES = {".tf", ".hcl", ".toml", ".properties", ".xml"}
SKIP_DIRS = {".git", ".poc-db", "node_modules", "vendor", "target", "build", ".venv", "venv", "__pycache__"}
MAX_CONFIG_FILES = 1000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_DOCUMENTS = 64
MAX_NODES_PER_FILE = 50_000
MAX_NESTING = 64
MAX_OBSERVATIONS_PER_FILE = 20_000
MAX_OBSERVATIONS_PER_SOURCE = 50_000
MAX_STRING_VALUE_LENGTH = 1000

_SENSITIVE_NAMES = {
    "password", "passwd", "secret", "secretkey", "clientsecret", "credential", "credentials",
    "apikey", "privatekey", "accesstoken", "refreshtoken", "idtoken", "token",
}
_SENSITIVE_NAME_SUFFIXES = (
    "password", "passwd", "secret", "credential", "credentials", "apikey", "privatekey",
    "accesskey", "accesskeyid", "accesstoken", "refreshtoken", "idtoken", "tokenvalue", "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bBearer\s+\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)://[^/@\s]+:[^/@\s]+@"),
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def observation_id(fact: dict[str, Any]) -> str:
    """Return a deterministic ID for a collector version and pinned source fact."""
    identity = {
        "schema_version": fact.get("schema_version", SCHEMA_VERSION),
        "predicate": fact.get("predicate"),
        "subject": fact.get("subject"),
        "value": fact.get("value"),
        "source_ref": fact.get("source_ref"),
        "collector": fact.get("collector"),
        "resolution": fact.get("resolution"),
        "evidence_class": fact.get("evidence_class"),
        "redacted": bool(fact.get("redacted", False)),
    }
    return "obs:" + hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()


def validate_observation(item: dict[str, Any]) -> None:
    """Reject observations that cannot be traced to an immutable source version."""
    if not isinstance(item, dict):
        raise ValueError("observation must be an object")
    if item.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported observation schema_version")
    for name in ("observation_id", "predicate", "evidence_class"):
        if not isinstance(item.get(name), str) or not item[name].strip():
            raise ValueError(f"observation requires non-empty {name}")
    if not isinstance(item.get("subject"), dict) or not item["subject"].get("id"):
        raise ValueError("observation requires subject.id")
    if not isinstance(item.get("source_ref"), dict):
        raise ValueError("observation requires source_ref")
    source_ref = item["source_ref"]
    for name in ("artifact_id", "version", "path"):
        if not isinstance(source_ref.get(name), str) or not source_ref[name].strip():
            raise ValueError(f"source_ref requires {name}")
    if not isinstance(source_ref.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source_ref["sha256"]):
        raise ValueError("source_ref requires a lowercase SHA-256 digest")
    if not isinstance(source_ref.get("locator"), dict) or not source_ref["locator"].get("kind"):
        raise ValueError("source_ref requires a typed locator")
    if not isinstance(item.get("collector"), dict) or not item["collector"].get("version"):
        raise ValueError("observation requires a versioned collector")
    if not isinstance(item.get("resolution"), dict) or item["resolution"].get("status") not in {
        "direct", "resolved", "approximate", "unresolved"
    }:
        raise ValueError("observation requires a recognized resolution status")
    if item.get("observation_id") != observation_id(item):
        raise ValueError("observation_id does not match canonical observation content")


def _make_observation(
    *, predicate: str, subject: dict[str, Any], value: Any, source_ref: dict[str, Any],
    collector: dict[str, Any], resolution: dict[str, Any], evidence_class: str,
    redacted: bool = False,
) -> dict[str, Any]:
    item = {
        "schema_version": SCHEMA_VERSION,
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "source_ref": source_ref,
        "collector": collector,
        "resolution": resolution,
        "evidence_class": evidence_class,
    }
    if redacted:
        item["redacted"] = True
    item["observation_id"] = observation_id(item)
    validate_observation(item)
    return item


def _source_ref(artifact: dict[str, Any], path: str, locator: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact.get("artifact_id", ""),
        "version": artifact.get("version", ""),
        "sha256": artifact.get("sha256", ""),
        "path": artifact.get("path") or path,
        "locator": locator,
    }


def from_callgraph(
    graph: dict[str, Any], artifact_map: dict[str, dict[str, Any]], *,
    source_root_relative: str = "", run_id: str,
) -> dict[str, Any]:
    """Normalize call edges while preserving language/resolver as collector metadata."""
    observations: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    edges = graph.get("edges", [])
    for edge in edges:
        relative = Path(source_root_relative, str(edge.get("path", ""))).as_posix()
        artifact = artifact_map.get(relative)
        if not artifact:
            missing_sources.append(relative)
            continue
        raw_status = str(edge.get("resolution_status", "unresolved"))
        status = "approximate" if "approximate" in raw_status else "unresolved" if raw_status.startswith(("unresolved", "external")) else "resolved"
        line = edge.get("line")
        locator = {"kind": "line", "start": line, "end": line} if isinstance(line, int) and line > 0 else {"kind": "symbol", "symbol": edge.get("caller_symbol_id", "")}
        source_ref = _source_ref(artifact, relative, locator)
        call_expression, call_redacted = redact_source_text(str(edge.get("call_expression", "")))
        caller_name, caller_redacted = redact_source_text(str(edge.get("caller_qualified_name", "")))
        target_name, target_redacted = redact_source_text(str(edge.get("callee_qualified_name", edge.get("callee_symbol_id", ""))))
        item = _make_observation(
            predicate="code.call_edge",
            subject={"id": str(edge.get("caller_symbol_id") or relative), "kind": "function", "name": caller_name},
            value={
                "target": target_name,
                "call_expression": call_expression,
                "edge_id": edge.get("edge_id", ""),
                "reachable_from_entry": bool(edge.get("reachable_from_entry")),
                "dispatch_kind": edge.get("dispatch_kind", "unknown"),
            },
            source_ref=source_ref,
            collector={"name": "language-callgraph", "version": CODE_COLLECTOR_VERSION,
                       "language": graph.get("language", "unknown"), "resolver": graph.get("resolver", "unknown"),
                       "resolution_basis": edge.get("resolution_basis", "unknown"), "run_id": run_id},
            resolution={"status": status, "source_status": raw_status,
                        "basis": edge.get("resolution_basis", "unknown")},
            evidence_class="static_code_observation", redacted=call_redacted or caller_redacted or target_redacted,
        )
        observations.append(item)
    return {
        "observations": observations,
        "coverage": {
            "source_type": "code",
            "collector": "language-callgraph",
            "complete": not missing_sources,
            "inspected_count": len(edges),
            "emitted_count": len(observations),
            "unresolved_count": sum(x["resolution"]["status"] == "unresolved" for x in observations),
            "approximate_count": sum(x["resolution"]["status"] == "approximate" for x in observations),
            "missing_source_refs": sorted(set(missing_sources)),
            "diagnostics": list(graph.get("diagnostics", [])),
        },
    }


def _normalized_key(value: str) -> str:
    # Split camelCase before removing punctuation, so tokenTTL and clientSecret
    # remain distinguishable without treating token lifetime as a credential.
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _looks_like_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
        return True
    if len(value) >= 32:
        alphabet = set(value)
        entropy = -sum((value.count(char) / len(value)) * math.log2(value.count(char) / len(value)) for char in alphabet)
        return entropy >= 4.2
    return False


_QUOTED_LITERAL = re.compile(r'''("""[\s\S]*?"""|''' + "'''[\\s\\S]*?'''" + r'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`[^`]*`)''')


def redact_source_text(value: str) -> tuple[str, bool]:
    """Remove literal payloads before source excerpts enter prompts or artifacts."""
    if not isinstance(value, str):
        return "", bool(value)
    redacted = _QUOTED_LITERAL.sub('"[redacted literal]"', value)
    if _looks_like_secret(redacted):
        return "[redacted sensitive source text]", True
    return redacted, redacted != value


def redact_source_values(value: Any) -> tuple[Any, bool]:
    """Recursively sanitize source-derived strings while retaining graph shape."""
    changed = False
    if isinstance(value, str):
        return redact_source_text(value)
    if isinstance(value, list):
        out = []
        for item in value:
            safe, item_changed = redact_source_values(item)
            out.append(safe); changed = changed or item_changed
        return out, changed
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            safe_key, key_changed = redact_source_text(str(key))
            safe, item_changed = redact_source_values(item)
            out[safe_key] = safe; changed = changed or key_changed or item_changed
        return out, changed
    return value, False


def _sensitive_path(keys: list[str], document: Any) -> bool:
    if not keys:
        return False
    kind = document.get("kind") if isinstance(document, dict) else None
    if str(kind).casefold() == "secret" and any(str(key).casefold() in {"data", "stringdata"} for key in keys):
        return True
    normalized = _normalized_key(keys[-1])
    return normalized in _SENSITIVE_NAMES or any(normalized.endswith(suffix) for suffix in _SENSITIVE_NAME_SUFFIXES)


def _plain_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        if isinstance(value, str) and len(value) > MAX_STRING_VALUE_LENGTH:
            return {"type": "string", "length": len(value), "truncated": True}
        return value
    if isinstance(value, (list, dict)):
        return {"type": "container", "size": len(value)}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)[:MAX_STRING_VALUE_LENGTH]


def _json_pointer(path: list[str | int]) -> str:
    def escape(part: str | int) -> str:
        return str(part).replace("~", "~0").replace("/", "~1")
    return "" if not path else "/" + "/".join(escape(part) for part in path)


def _subject(document: Any, path: str, document_index: int) -> dict[str, Any]:
    if isinstance(document, dict):
        kind = document.get("kind") or document.get("Type") or document.get("type")
        metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        name = metadata.get("name") or document.get("name") or document.get("Name")
        namespace = metadata.get("namespace")
        api_version = document.get("apiVersion") or document.get("AWSTemplateFormatVersion")
        if name or kind:
            identity = ":".join(str(part) for part in (api_version or "config", kind or "object", namespace or "", name or f"document-{document_index}") if part != "")
            return {"id": identity, "kind": str(kind or "configuration_object"), "name": str(name or ""), "namespace": str(namespace or "")}
    return {"id": f"config:{path}:document-{document_index}", "kind": "configuration_document", "name": Path(path).name}


def _walk_node(
    node: Node, document: Any, path_parts: list[str | int], *,
    source_file: str, artifact: dict[str, Any], collector_format: str,
    subject: dict[str, Any], active: set[int], count: list[int], observations: list[dict[str, Any]],
    redacted_count: list[int],
) -> None:
    count[0] += 1
    if count[0] > MAX_NODES_PER_FILE:
        raise ValueError(f"node limit {MAX_NODES_PER_FILE} exceeded")
    if len(path_parts) > MAX_NESTING:
        raise ValueError(f"nesting limit {MAX_NESTING} exceeded")
    identity = id(node)
    if identity in active:
        raise ValueError("recursive YAML alias encountered")
    active.add(identity)
    try:
        if isinstance(node, MappingNode):
            seen_keys: set[str] = set()
            for key_node, child in node.value:
                if not isinstance(key_node, ScalarNode):
                    raise ValueError("non-scalar mapping key is unsupported")
                key = str(key_node.value)
                if key in seen_keys:
                    raise ValueError(f"duplicate mapping key {key!r} is ambiguous")
                seen_keys.add(key)
                child_parts = path_parts + [key]
                if _sensitive_path([str(x) for x in child_parts], document):
                    locator = {"kind": "json_pointer" if collector_format == "json" else "yaml_path",
                               "pointer": _json_pointer(child_parts), "path": child_parts,
                               "line": child.start_mark.line + 1, "column": child.start_mark.column + 1}
                    source_ref = _source_ref(artifact, source_file, locator)
                    observation = _make_observation(
                        predicate="configuration.property",
                        subject=subject,
                        value=None,
                        source_ref=source_ref,
                        collector={"name": "structured-config", "version": CONFIG_COLLECTOR_VERSION, "format": collector_format},
                        resolution={"status": "direct", "basis": "parsed_configuration"},
                        evidence_class="declared_configuration",
                        redacted=True,
                    )
                    observations.append(observation)
                    redacted_count[0] += 1
                    if len(observations) > MAX_OBSERVATIONS_PER_FILE:
                        raise ValueError(f"observation limit {MAX_OBSERVATIONS_PER_FILE} exceeded")
                    continue
                _walk_node(child, document, child_parts, source_file=source_file, artifact=artifact,
                           collector_format=collector_format, subject=subject, active=active,
                           count=count, observations=observations, redacted_count=redacted_count)
        elif isinstance(node, SequenceNode):
            for index, child in enumerate(node.value):
                _walk_node(child, document, path_parts + [index], source_file=source_file,
                           artifact=artifact, collector_format=collector_format, subject=subject,
                           active=active, count=count, observations=observations, redacted_count=redacted_count)
            if not node.value:
                _emit_leaf(node, document, path_parts, source_file, artifact, collector_format, subject, observations, redacted_count)
        elif isinstance(node, ScalarNode):
            _emit_leaf(node, document, path_parts, source_file, artifact, collector_format, subject, observations, redacted_count)
    finally:
        active.remove(identity)


def _value_at(document: Any, path_parts: list[str | int]) -> Any:
    current = document
    for part in path_parts:
        if isinstance(current, dict):
            # YAML scalar mapping keys can be non-strings. The collector only
            # emits string-keyed paths to keep locators stable and interoperable.
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return None
    return current


def _emit_leaf(
    node: Node, document: Any, path_parts: list[str | int], source_file: str,
    artifact: dict[str, Any], collector_format: str, subject: dict[str, Any],
    observations: list[dict[str, Any]], redacted_count: list[int],
) -> None:
    value = _value_at(document, path_parts)
    if _looks_like_secret(value):
        value = None
        redacted = True
        redacted_count[0] += 1
    else:
        value = _plain_value(value)
        redacted = False
    locator = {"kind": "json_pointer" if collector_format == "json" else "yaml_path",
               "pointer": _json_pointer(path_parts), "path": path_parts,
               "line": node.start_mark.line + 1, "column": node.start_mark.column + 1}
    observations.append(_make_observation(
        predicate="configuration.property",
        subject=subject,
        value=value,
        source_ref=_source_ref(artifact, source_file, locator),
        collector={"name": "structured-config", "version": CONFIG_COLLECTOR_VERSION, "format": collector_format},
        resolution={"status": "direct", "basis": "parsed_configuration"},
        evidence_class="declared_configuration",
        redacted=redacted,
    ))
    if len(observations) > MAX_OBSERVATIONS_PER_FILE:
        raise ValueError(f"observation limit {MAX_OBSERVATIONS_PER_FILE} exceeded")


def _parse_documents(text: str) -> list[tuple[Node, Any]]:
    loader = yaml.SafeLoader(text)
    parsed: list[tuple[Node, Any]] = []
    try:
        while loader.check_data():
            if len(parsed) >= MAX_DOCUMENTS:
                raise ValueError(f"document limit {MAX_DOCUMENTS} exceeded")
            node = loader.get_node()
            value = loader.construct_document(node)
            if node is not None:
                parsed.append((node, value))
    finally:
        loader.dispose()
    return parsed


def _candidate_files(root: Path) -> tuple[list[Path], list[Path]]:
    supported: list[Path] = []
    unsupported: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        suffix = path.suffix.lower()
        if suffix in CONFIG_SUFFIXES:
            supported.append(path)
        elif suffix in RECOGNIZED_UNSUPPORTED_SUFFIXES:
            unsupported.append(path)
    return supported, unsupported


def _safe_diagnostic_code(error: Exception) -> str:
    """Return a bounded category; parser messages can echo attacker-controlled source text."""
    if isinstance(error, UnicodeDecodeError):
        return "invalid_utf8"
    if isinstance(error, yaml.YAMLError):
        return "invalid_yaml_or_json"
    detail = str(error)
    if detail.startswith("duplicate mapping key"):
        return "duplicate_mapping_key"
    if "limit" in detail:
        return "resource_limit_exceeded"
    if "recursive YAML alias" in detail:
        return "recursive_yaml_alias"
    if "non-scalar mapping key" in detail:
        return "unsupported_mapping_key"
    return "collection_error"


def discover_configuration_files(root: str | Path) -> tuple[list[Path], list[Path]]:
    """Return supported and recognized unsupported files under a config root."""
    return _candidate_files(Path(root).resolve())


def collect_configuration(root: str | Path, artifact_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Flatten YAML/JSON scalar properties into pinned facts; never execute templates."""
    base = Path(root).resolve()
    observations: list[dict[str, Any]] = []
    supported, unsupported = _candidate_files(base)
    if len(supported) > MAX_CONFIG_FILES:
        unsupported.extend(supported[MAX_CONFIG_FILES:])
        supported = supported[:MAX_CONFIG_FILES]
    failed_files: list[str] = []
    diagnostics: list[dict[str, str]] = []
    redacted_values = 0
    inspected = 0
    for path in supported:
        relative = path.relative_to(base).as_posix()
        if len(observations) >= MAX_OBSERVATIONS_PER_SOURCE:
            remaining = [candidate.relative_to(base).as_posix() for candidate in supported if candidate >= path]
            failed_files.extend(remaining)
            diagnostics.append({"path": relative, "error": f"source observation limit {MAX_OBSERVATIONS_PER_SOURCE} exceeded"})
            break
        inspected += 1
        artifact = artifact_map.get(relative)
        if not artifact:
            failed_files.append(relative)
            diagnostics.append({"path": relative, "error_code": "source_version_not_pinned"})
            continue
        try:
            data = path.read_bytes()
            if len(data) > MAX_FILE_BYTES:
                raise ValueError(f"file size exceeds {MAX_FILE_BYTES} bytes")
            text = data.decode("utf-8")
            documents = _parse_documents(text)
            file_observations: list[dict[str, Any]] = []
            file_redacted = [0]
            for doc_index, (node, document) in enumerate(documents, start=1):
                if node is None:
                    continue
                subject = _subject(document, relative, doc_index)
                _walk_node(node, document, [], source_file=relative, artifact=artifact,
                           collector_format="json" if path.suffix.lower() == ".json" else "yaml",
                           subject=subject, active=set(), count=[0], observations=file_observations,
                           redacted_count=file_redacted)
                if len(observations) + len(file_observations) > MAX_OBSERVATIONS_PER_SOURCE:
                    raise ValueError(f"source observation limit {MAX_OBSERVATIONS_PER_SOURCE} exceeded")
            observations.extend(file_observations)
            redacted_values += file_redacted[0]
        except Exception as error:
            failed_files.append(relative)
            diagnostics.append({"path": relative, "error_code": _safe_diagnostic_code(error)})
    unsupported_files = [path.relative_to(base).as_posix() for path in unsupported]
    return {
        "observations": observations,
        "coverage": {
            "source_type": "configuration",
            "collector": "structured-config",
            "collector_version": CONFIG_COLLECTOR_VERSION,
            "complete": not failed_files and not unsupported_files,
            "inspected_count": inspected,
            "emitted_count": len(observations),
            "redacted_value_count": redacted_values,
            "failed_files": sorted(failed_files),
            "unsupported_files": sorted(unsupported_files),
            "diagnostics": diagnostics,
            "scope_root": ".",
        },
    }


def to_evidence(item: dict[str, Any], evidence_id: str | None = None) -> dict[str, Any]:
    """Create an evidence-index item without copying arbitrary source text."""
    validate_observation(item)
    source_ref = item["source_ref"]
    locator = source_ref["locator"]
    if item.get("redacted"):
        excerpt = "[redacted sensitive configuration value]"
        claim_value = "[redacted]"
    else:
        value = item.get("value")
        claim_value = _canonical(value)
        excerpt = claim_value[:MAX_STRING_VALUE_LENGTH]
    return {
        "evidence_id": evidence_id or item["observation_id"],
        "observation_id": item["observation_id"],
        "evidence_type": "configuration_property" if item["predicate"] == "configuration.property" else "source_observation",
        "artifact_id": source_ref["artifact_id"],
        "artifact_version": source_ref["version"],
        "path": source_ref["path"],
        "start_line": locator.get("line"),
        "end_line": locator.get("line"),
        "source_locator": locator,
        "claim": f"Observed {item['predicate']} on {item['subject'].get('id')}: {claim_value}",
        "excerpt": excerpt,
        "sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        "resolution_status": item["resolution"]["status"],
        "redacted": bool(item.get("redacted")),
    }
