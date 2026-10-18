"""Offline JSON configuration collector bound by predicate registry.

Reads pinned JSON content through a JSON Pointer. Does not invent values when
the pointer is missing or the value type mismatches the registered predicate.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import predicate_registry

COLLECTOR_ID = "config_json"


class ConfigCollectionError(ValueError):
    """Pinned configuration cannot safely yield an observation."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigCollectionError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str):
        raise ConfigCollectionError("JSON Pointer must be a string")
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ConfigCollectionError("JSON Pointer must be empty or begin with '/'")
    value = document
    for raw_token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw_token):
            raise ConfigCollectionError("invalid JSON Pointer escape")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if token not in value:
                raise ConfigCollectionError("JSON Pointer object member does not exist")
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ConfigCollectionError("JSON Pointer array index is not canonical")
            index = int(token)
            if index >= len(value):
                raise ConfigCollectionError("JSON Pointer array index is out of range")
            value = value[index]
        else:
            raise ConfigCollectionError("JSON Pointer traverses a scalar value")
    return value


def _coerce_value(value_type: str, value: Any) -> Any:
    if value_type == "number":
        if type(value) not in (int, float) or isinstance(value, bool):
            raise ConfigCollectionError("expected a JSON number")
        return value
    if value_type == "boolean":
        if type(value) is not bool:
            raise ConfigCollectionError("expected a JSON boolean")
        return value
    if value_type == "string":
        if not isinstance(value, str) or not value.strip():
            raise ConfigCollectionError("expected a non-empty JSON string")
        return value
    raise ConfigCollectionError(f"unsupported value type {value_type!r}")


def collect_config_observation(
    *,
    content: str,
    pointer: str,
    predicate: str,
    subject: str,
    evidence_id: str,
    artifact_id: str,
    revision: str,
    path: str,
) -> dict[str, Any]:
    """Collect one observation for a registry-backed configuration predicate."""
    if predicate_registry.collector_for(predicate) != COLLECTOR_ID:
        raise predicate_registry.CapabilityError(
            f"predicate {predicate!r} is not collected by {COLLECTOR_ID}"
        )
    meta = predicate_registry.get_predicate(predicate)
    for field, value in (
        ("subject", subject),
        ("evidence_id", evidence_id),
        ("artifact_id", artifact_id),
        ("revision", revision),
        ("path", path),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
    try:
        document = json.loads(content, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, ConfigCollectionError) as exc:
        raise ConfigCollectionError(f"invalid JSON content: {exc}") from exc
    resolved = resolve_json_pointer(document, pointer)
    typed = _coerce_value(meta["value_type"], resolved)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "evidence_id": evidence_id,
        "predicate": predicate,
        "subject": subject,
        "value": typed,
        "artifact_id": artifact_id,
        "revision": revision,
        "path": path,
        "source_sha256": digest,
        "locator": {"kind": "json_pointer", "pointer": pointer, "value": pointer},
        "collector": COLLECTOR_ID,
    }
