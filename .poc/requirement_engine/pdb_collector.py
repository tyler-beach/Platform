"""Conservative offline Kubernetes PodDisruptionBudget manifest collector."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

PDB_PREDICATE = "kubernetes.pod_disruption_budget.present"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "ReplicationController"}
YAML_SUFFIXES = {".yaml", ".yml"}


class ManifestError(ValueError):
    """A manifest set cannot safely support a positive or negative conclusion."""


class UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ManifestError("unhashable YAML mapping key") from exc
        if duplicate:
            raise ManifestError(f"duplicate YAML mapping key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_manifests(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not root.exists() or not root.is_dir():
        raise ManifestError("manifest root must be an existing directory")
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in YAML_SUFFIXES)
    if not paths:
        raise ManifestError("no YAML manifests found; absence cannot be established")
    documents: list[dict[str, Any]] = []
    inventory: list[dict[str, str]] = []
    for path in paths:
        raw = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        inventory.append({"path": relative, "sha256": _sha256(raw)})
        try:
            parsed = list(yaml.load_all(raw.decode("utf-8"), Loader=UniqueKeySafeLoader))
        except (UnicodeDecodeError, yaml.YAMLError, ManifestError) as exc:
            raise ManifestError(f"cannot safely parse {relative}: {exc}") from exc
        for index, document in enumerate(parsed):
            if document is None:
                continue
            if not isinstance(document, dict):
                raise ManifestError(f"{relative} document {index + 1} must be a YAML object")
            if not isinstance(document.get("kind"), str) or not isinstance(document.get("apiVersion"), str):
                raise ManifestError(f"{relative} document {index + 1} requires apiVersion and kind")
            metadata = document.get("metadata")
            if not isinstance(metadata, dict) or not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
                raise ManifestError(f"{relative} document {index + 1} requires metadata.name")
            documents.append({
                "document": document,
                "path": relative,
                "document_index": index,
                "sha256": _sha256(raw),
            })
    return documents, inventory


def _namespace(document: dict[str, Any]) -> str:
    return document.get("metadata", {}).get("namespace") or "default"


def _labels(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise ManifestError(f"{where} must be a string-to-string label map")
    return value


def _selector_matches(selector: Any, labels: dict[str, str]) -> bool:
    if selector is None:
        # policy/v1 with selector:null selects no pods; do not interpret it as all.
        return False
    if not isinstance(selector, dict):
        raise ManifestError("PDB spec.selector must be an object or null")
    match_labels = selector.get("matchLabels", {})
    if not isinstance(match_labels, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in match_labels.items()):
        raise ManifestError("PDB selector.matchLabels must be a string-to-string map")
    if any(labels.get(key) != value for key, value in match_labels.items()):
        return False
    expressions = selector.get("matchExpressions", [])
    if not isinstance(expressions, list):
        raise ManifestError("PDB selector.matchExpressions must be a list")
    for expression in expressions:
        if not isinstance(expression, dict) or not isinstance(expression.get("key"), str):
            raise ManifestError("PDB selector expression requires a key")
        key, operator = expression["key"], expression.get("operator")
        values = expression.get("values", [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ManifestError("PDB selector expression values must be strings")
        present = key in labels
        if operator == "In":
            matched = present and labels[key] in values
        elif operator == "NotIn":
            matched = not present or labels[key] not in values
        elif operator == "Exists":
            matched = present and not values
        elif operator == "DoesNotExist":
            matched = not present and not values
        else:
            raise ManifestError(f"unsupported PDB selector operator: {operator!r}")
        if not matched:
            return False
    return True


def collect_pdb_observation(
    root: str | Path,
    *,
    workload_name: str,
    namespace: str = "default",
    evidence_id: str = "PDB-COLLECTOR-1",
    artifact_id: str = "kubernetes-manifest-bundle",
    revision: str,
) -> dict[str, Any]:
    """Return one observation only when the manifest inventory is parseable and scoped.

    A negative observation means no PDB in the complete supplied YAML inventory
    selects the target workload's pod-template labels in its namespace. It does
    not prove anything about manifests omitted from that inventory or live cluster state.
    """
    for field, value in (("workload_name", workload_name), ("namespace", namespace),
                         ("evidence_id", evidence_id), ("artifact_id", artifact_id), ("revision", revision)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
    documents, inventory = _read_manifests(Path(root))
    workloads = []
    pdbs = []
    for item in documents:
        document = item["document"]
        metadata = document["metadata"]
        if document["kind"] in WORKLOAD_KINDS and metadata["name"] == workload_name and _namespace(document) == namespace:
            template = document.get("spec", {}).get("template", {})
            pod_metadata = template.get("metadata", {}) if isinstance(template, dict) else {}
            if not isinstance(pod_metadata, dict):
                raise ManifestError(f"{item['path']} workload pod-template metadata must be an object")
            labels = _labels(pod_metadata.get("labels", {}), f"{item['path']} pod-template labels")
            workloads.append({**item, "labels": labels})
        elif document["kind"] == "Pod" and metadata["name"] == workload_name and _namespace(document) == namespace:
            workloads.append({**item, "labels": _labels(metadata.get("labels", {}), f"{item['path']} pod labels")})
        if document["kind"] == "PodDisruptionBudget" and _namespace(document) == namespace:
            spec = document.get("spec")
            if not isinstance(spec, dict):
                raise ManifestError(f"{item['path']} PDB spec must be an object")
            pdbs.append({**item, "selector": spec.get("selector")})
    if not workloads:
        raise ManifestError(f"target workload {namespace}/{workload_name} was not found; absence is not evidence")
    labels = workloads[0]["labels"]
    if any(workload["labels"] != labels for workload in workloads[1:]):
        raise ManifestError(f"multiple target workload definitions disagree for {namespace}/{workload_name}")
    matches = []
    for pdb in pdbs:
        if _selector_matches(pdb["selector"], labels):
            matches.append(pdb)
    # Empty selector in policy/v1 selects all pods; explicit null selects none.
    value = bool(matches)
    if matches:
        source = sorted(matches, key=lambda item: (item["path"], item["document_index"]))[0]
        source_path = source["path"]
        source_hash = source["sha256"]
        locator = {
            "kind": "yaml_resource",
            "value": f"PodDisruptionBudget/{source['document']['metadata']['name']}",
            "document_index": source["document_index"],
            "workload": f"{namespace}/{workload_name}",
            "matching_pdbs": sorted(item["document"]["metadata"]["name"] for item in matches),
            "inventory": inventory,
        }
    else:
        # Negative evidence is rooted in the target workload and the complete scanned inventory.
        source = workloads[0]
        source_path = source["path"]
        source_hash = source["sha256"]
        locator = {
            "kind": "manifest_inventory",
            "workload": f"{namespace}/{workload_name}",
            "matching_pdbs": [],
            "inventory": inventory,
            "scope_note": "No matching PDB was found in the complete supplied manifest inventory.",
        }
    return {
        "evidence_id": evidence_id,
        "predicate": PDB_PREDICATE,
        "subject": f"{namespace}/{workload_name}",
        "value": value,
        "artifact_id": artifact_id,
        "revision": revision,
        "path": source_path,
        "source_sha256": source_hash,
        "locator": locator,
    }
