"""Predicate catalog and collector capability map.

Collectors bind by evidence domain and predicate, never by ADR identifier.
Unknown predicates fail closed rather than inventing observations.
"""
from __future__ import annotations

from typing import Any

REGISTRY_VERSION = "predicate-registry-v1"

# value_type: how engine.evaluate interprets observation.value for the kind family.
PREDICATES: dict[str, dict[str, Any]] = {
    "session.ttl_seconds": {
        "value_type": "number",
        "collector": "config_json",
        "description": "Configured or observed session lifetime in seconds",
        "compatible_kinds": ("numeric_max",),
    },
    "kubernetes.pod_disruption_budget.present": {
        "value_type": "boolean",
        "collector": "kubernetes_manifest",
        "description": "Whether a PDB in the supplied inventory selects the workload",
        "compatible_kinds": ("resource_present", "boolean_required"),
    },
    "security.encryption_at_rest.enabled": {
        "value_type": "boolean",
        "collector": "config_json",
        "description": "Whether encryption at rest is enabled in pinned config",
        "compatible_kinds": ("boolean_required",),
    },
    "security.tls_policy.id": {
        "value_type": "string",
        "collector": "config_json",
        "description": "Configured TLS policy identifier",
        "compatible_kinds": ("set_membership",),
    },
}

COLLECTORS: dict[str, dict[str, Any]] = {
    "config_json": {
        "domain": "configuration",
        "predicates": sorted(
            name for name, meta in PREDICATES.items() if meta["collector"] == "config_json"
        ),
        "inputs": ("pinned JSON artifact", "JSON Pointer locator"),
    },
    "kubernetes_manifest": {
        "domain": "kubernetes",
        "predicates": sorted(
            name for name, meta in PREDICATES.items() if meta["collector"] == "kubernetes_manifest"
        ),
        "inputs": ("offline YAML inventory", "workload name", "namespace"),
    },
}


class CapabilityError(ValueError):
    """Requested predicate has no registered collector capability."""


def get_predicate(predicate: str) -> dict[str, Any]:
    if not isinstance(predicate, str) or predicate not in PREDICATES:
        raise CapabilityError(f"unknown predicate: {predicate!r}")
    return dict(PREDICATES[predicate])


def collector_for(predicate: str) -> str:
    return get_predicate(predicate)["collector"]


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
        "collectors": {
            name: {"domain": meta["domain"], "predicates": list(meta["predicates"])}
            for name, meta in sorted(COLLECTORS.items())
        },
    }
