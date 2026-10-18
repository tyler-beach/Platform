"""End-to-end offline adapter: Kubernetes manifest evidence -> shared ADR evaluator.

This adapter deliberately treats collection failures as inconclusive evidence gaps.
It does not query a cluster, infer ADR scope, or parse natural-language ADRs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import engine
import predicate_registry
from pdb_collector import ManifestError, collect_pdb_observation

PDB_PREDICATE = "kubernetes.pod_disruption_budget.present"
PDB_REQUIREMENT = {
    "requirement_id": "ADR-PDB-001",
    "kind": "resource_present",
    "predicate": PDB_PREDICATE,
}


def evaluate_pdb(
    manifest_root: str | Path,
    *,
    workload_name: str,
    namespace: str,
    revision: str,
    artifact_id: str,
    adr_status: str = "accepted",
    scope_match: bool = True,
) -> dict[str, Any]:
    """Collect and evaluate one named workload against an accepted PDB requirement.

    A collection error produces an explicit inconclusive result with no fabricated
    observation. Scope is supplied by the caller; this prototype does not infer it.
    """
    requirement = {
        **PDB_REQUIREMENT,
        "subject": f"{namespace}/{workload_name}",
    }
    # Bind through the shared capability map; collectors are domain-scoped, not ADR-scoped.
    predicate_registry.asserts_compatible(requirement["kind"], requirement["predicate"])
    if predicate_registry.collector_for(requirement["predicate"]) != "kubernetes_manifest":
        raise predicate_registry.CapabilityError("PDB evaluation requires the kubernetes_manifest collector")

    # Applicability is decided before collection: out-of-scope ADRs do not need
    # implementation evidence and must not be reported as compliant/deviating.
    if adr_status != "accepted" or not scope_match:
        return engine.evaluate(
            requirement, [], adr_status=adr_status, scope_match=scope_match
        )

    try:
        observation = collect_pdb_observation(
            manifest_root,
            workload_name=workload_name,
            namespace=namespace,
            evidence_id=f"PDB:{namespace}/{workload_name}:{revision}",
            artifact_id=artifact_id,
            revision=revision,
        )
    except ManifestError as exc:
        result: dict[str, Any] = {
            "schema_version": engine.RESULT_SCHEMA_VERSION,
            "engine_version": engine.ENGINE_VERSION,
            "requirement": requirement,
            "applicability": {
                "applicable": True,
                "adr_status": adr_status,
                "scope_match": scope_match,
            },
            "outcome": "inconclusive",
            "relationship": "insufficient_evidence",
            "rationale": "The manifest collector could not establish a safe observation.",
            "considered_evidence_ids": [],
            "accepted_evidence_ids": [],
            "rejected_evidence_ids": [],
            "uncertainty": ["collection_failed"],
            "evidence_gap": {"code": "manifest_collection_failed", "detail": str(exc)},
            "provenance": [],
        }
        result["result_sha256"] = engine.fingerprint(result)
        return result

    return engine.evaluate(
        requirement,
        [observation],
        adr_status=adr_status,
        scope_match=scope_match,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one Kubernetes workload's PDB requirement using offline YAML evidence."
    )
    parser.add_argument("manifest_root", type=Path, help="directory containing the complete YAML manifest inventory")
    parser.add_argument("--workload", required=True, help="workload name")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--revision", required=True, help="immutable source revision identifier")
    parser.add_argument("--artifact-id", default="kubernetes-manifest-bundle")
    parser.add_argument("--adr-status", choices=("accepted", "proposed", "superseded"), default="accepted")
    parser.add_argument("--out-of-scope", action="store_true", help="explicitly mark this workload outside the ADR scope")
    args = parser.parse_args()

    try:
        result = evaluate_pdb(
            args.manifest_root,
            workload_name=args.workload,
            namespace=args.namespace,
            revision=args.revision,
            artifact_id=args.artifact_id,
            adr_status=args.adr_status,
            scope_match=not args.out_of_scope,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["outcome"] != "inconclusive" else 2


if __name__ == "__main__":
    raise SystemExit(main())
