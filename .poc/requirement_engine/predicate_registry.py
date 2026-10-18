"""Predicate catalog and collector capability map.

Collectors bind by evidence domain and predicate, never by ADR identifier.
Unknown predicates fail closed rather than inventing observations.

Loads the multi-ADR catalog seed from `.poc/requirement_catalog/predicates.json`
when present, and merges built-in bootstrap predicates.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_VERSION = "predicate-registry-v2"

_BUILTIN: dict[str, dict[str, Any]] = {
    "session.ttl_seconds": {
        "value_type": "number",
        "collector": "config_json",
        "description": "Configured or observed session lifetime in seconds",
        "compatible_kinds": ["numeric_max"],
    },
    "kubernetes.pod_disruption_budget.present": {
        "value_type": "boolean",
        "collector": "kubernetes_manifest",
        "description": "Whether a PDB in the supplied inventory selects the workload",
        "compatible_kinds": ["resource_present", "boolean_required"],
    },
    "security.encryption_at_rest.enabled": {
        "value_type": "boolean",
        "collector": "config_json",
        "description": "Whether encryption at rest is enabled in pinned config",
        "compatible_kinds": ["boolean_required"],
    },
    "security.tls_policy.id": {
        "value_type": "string",
        "collector": "config_json",
        "description": "Configured TLS policy identifier",
        "compatible_kinds": ["set_membership"],
    },
}

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "requirement_catalog" / "predicates.json"


def _load_predicates() -> dict[str, dict[str, Any]]:
    merged = {key: dict(value) for key, value in _BUILTIN.items()}
    if _CATALOG_PATH.exists():
        payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        for name, meta in payload.get("predicates", {}).items():
            current = merged.get(name, {})
            kinds = set(current.get("compatible_kinds", [])) | set(meta.get("compatible_kinds", []))
            domains = set(current.get("domains", [])) | set(meta.get("domains", []))
            merged[name] = {
                **current,
                **meta,
                "compatible_kinds": sorted(kinds),
                "domains": sorted(domains) if domains else meta.get("domains", []),
                # Prefer structured_package for catalog predicates; keep specialized collectors when builtin.
                "collector": current.get("collector")
                if name in _BUILTIN and meta.get("collector") == "structured_package"
                else meta.get("collector", current.get("collector", "structured_package")),
            }
            # Catalog predicates should remain collectable via structured packages even when a
            # specialized collector also exists.
            if merged[name]["collector"] in {"config_json", "kubernetes_manifest"}:
                merged[name]["also_collectors"] = sorted(
                    set(merged[name].get("also_collectors", [])) | {"structured_package"}
                )
    return merged


PREDICATES: dict[str, dict[str, Any]] = _load_predicates()


def _collector_index() -> dict[str, dict[str, Any]]:
    collectors: dict[str, dict[str, Any]] = {}
    for name, meta in PREDICATES.items():
        for collector_id in [meta["collector"], *meta.get("also_collectors", [])]:
            bucket = collectors.setdefault(
                collector_id,
                {"domain": collector_id, "predicates": [], "inputs": ("pinned evidence package or domain artifacts",)},
            )
            if name not in bucket["predicates"]:
                bucket["predicates"].append(name)
    for bucket in collectors.values():
        bucket["predicates"] = sorted(bucket["predicates"])
    return collectors


COLLECTORS: dict[str, dict[str, Any]] = _collector_index()


class CapabilityError(ValueError):
    """Requested predicate has no registered collector capability."""


def reload() -> None:
    """Reload registry from disk (tests / generator)."""
    global PREDICATES, COLLECTORS
    PREDICATES = _load_predicates()
    COLLECTORS = _collector_index()


def get_predicate(predicate: str) -> dict[str, Any]:
    if not isinstance(predicate, str) or predicate not in PREDICATES:
        raise CapabilityError(f"unknown predicate: {predicate!r}")
    return dict(PREDICATES[predicate])


def collector_for(predicate: str) -> str:
    return get_predicate(predicate)["collector"]


def collectors_for(predicate: str) -> list[str]:
    meta = get_predicate(predicate)
    return sorted({meta["collector"], *meta.get("also_collectors", [])})


def asserts_compatible(kind: str, predicate: str) -> None:
    meta = get_predicate(predicate)
    if kind not in meta["compatible_kinds"]:
        raise CapabilityError(
            f"predicate {predicate!r} is not compatible with kind {kind!r}; "
            f"allowed={list(meta['compatible_kinds'])}"
        )


def list_capabilities() -> dict[str, Any]:
    return {
        "registry_version": REGISTRY_VERSION,
        "predicates": sorted(PREDICATES),
        "predicate_count": len(PREDICATES),
        "collectors": {
            name: {"domain": meta["domain"], "predicates": list(meta["predicates"])}
            for name, meta in sorted(COLLECTORS.items())
        },
    }
