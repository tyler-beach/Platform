"""Collect observations from a pinned structured evidence package.

A package may include tech_spec and code artifacts plus explicit observations.
This collector validates observations against the predicate registry and pins
artifact hashes. It does not invent values for missing predicates.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import predicate_registry

PACKAGE_SCHEMA = "pathfinder-evidence-package-v1"
COLLECTOR_ID = "structured_package"


class PackageError(ValueError):
    """Evidence package cannot safely yield observations."""


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_package(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    try:
        package = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PackageError(f"package is not valid JSON: {exc}") from exc
    if not isinstance(package, dict):
        raise PackageError("package must be an object")
    if package.get("schema_version") != PACKAGE_SCHEMA:
        raise PackageError(f"unsupported package schema_version: {package.get('schema_version')!r}")
    return package


def _validate_observation(item: Any, index: int, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PackageError(f"observations[{index}] must be an object")
    for field in ("evidence_id", "predicate", "subject", "artifact_id", "revision", "path"):
        if not _nonempty_string(item.get(field)):
            raise PackageError(f"observations[{index}].{field} must be a non-empty string")
    meta = predicate_registry.get_predicate(item["predicate"])
    if COLLECTOR_ID not in predicate_registry.collectors_for(item["predicate"]):
        raise PackageError(
            f"observations[{index}] predicate {item['predicate']!r} is not collectable via {COLLECTOR_ID}"
        )
    locator = item.get("locator")
    if not isinstance(locator, dict) or not _nonempty_string(locator.get("kind")):
        raise PackageError(f"observations[{index}].locator must be typed")
    value = item.get("value")
    value_type = meta["value_type"]
    if value_type == "number" and (type(value) not in (int, float) or isinstance(value, bool)):
        raise PackageError(f"observations[{index}] expected number")
    if value_type == "boolean" and type(value) is not bool:
        raise PackageError(f"observations[{index}] expected boolean")
    if value_type == "string" and not _nonempty_string(value):
        raise PackageError(f"observations[{index}] expected string")
    source_sha = item.get("source_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source_sha or "")):
        artifact = artifacts.get(item["artifact_id"])
        if not artifact:
            raise PackageError(f"observations[{index}] missing source_sha256 and unknown artifact_id")
        source_sha = artifact["sha256"]
    return {
        "evidence_id": item["evidence_id"],
        "predicate": item["predicate"],
        "subject": item["subject"],
        "value": value,
        "artifact_id": item["artifact_id"],
        "revision": item["revision"],
        "path": item["path"],
        "source_sha256": source_sha,
        "locator": locator,
        "collector": COLLECTOR_ID,
    }


def collect_package_observations(package: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated observations from the package; never synthesize missing ones."""
    artifacts: dict[str, dict[str, Any]] = {}
    for field in ("tech_spec",):
        block = package.get(field)
        if isinstance(block, dict) and _nonempty_string(block.get("content")):
            digest = block.get("sha256") or _sha256_text(block["content"])
            if block.get("sha256") and block["sha256"] != _sha256_text(block["content"]):
                raise PackageError(f"{field} sha256 does not match content")
            artifacts[block.get("artifact_id", field)] = {
                "sha256": digest,
                "path": block.get("path", field),
                "revision": block.get("revision", f"sha256:{digest}"),
            }
    for index, block in enumerate(package.get("code") or []):
        if not isinstance(block, dict) or not _nonempty_string(block.get("content")):
            raise PackageError(f"code[{index}] requires content")
        digest = block.get("sha256") or _sha256_text(block["content"])
        if block.get("sha256") and block["sha256"] != digest:
            raise PackageError(f"code[{index}] sha256 does not match content")
        artifacts[block.get("artifact_id", f"code-{index}")] = {
            "sha256": digest,
            "path": block.get("path", f"code-{index}"),
            "revision": block.get("revision", f"sha256:{digest}"),
        }

    observations_in = package.get("observations")
    if observations_in is None:
        return []
    if not isinstance(observations_in, list):
        raise PackageError("observations must be a list")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for index, item in enumerate(observations_in):
        obs = _validate_observation(item, index, artifacts)
        if obs["evidence_id"] in seen:
            raise PackageError("observation evidence_ids must be unique")
        seen.add(obs["evidence_id"])
        out.append(obs)
    return out
