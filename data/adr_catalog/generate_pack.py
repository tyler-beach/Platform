#!/usr/bin/env python3
"""Generate the prototype real ADR catalog pack under data/adr_catalog/.

These ADRs are stand-ins for a working prototype. Replace with org ADRs later
(see README.md). Run from repo root:

  python3 data/adr_catalog/generate_pack.py
"""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PRED_SRC = REPO / ".poc" / "requirement_catalog" / "predicates.json"

# Prototype corpus: (adr_id, title, domain, kind, predicate, subject, limit|None, approved_set|None, decision)
# Limits chosen to be realistic platform policy and extractable by paste heuristics.
CORPUS: list[dict] = [
    {
        "adr_id": "ADR-PLATFORM-001",
        "file": "POD-DISRUPTION-BUDGETS.md",
        "title": "Preserve availability during voluntary disruption",
        "domain": "reliability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-001-REQ-1",
                "kind": "resource_present",
                "predicate": "kubernetes.pod_disruption_budget.present",
                "subject": "workload",
                "decision": "Availability-sensitive workloads MUST declare and maintain a PodDisruptionBudget.",
            },
            {
                "requirement_id": "ADR-PLATFORM-001-REQ-2",
                "kind": "numeric_min",
                "predicate": "kubernetes.pod_disruption_budget.min_available",
                "subject": "workload",
                "limit": 2,
                "decision": "Tier-1 disruption budgets MUST keep at least two pods available.",
            },
        ],
        "body": textwrap.dedent("""\
            # ADR-PLATFORM-001 — Preserve service availability during voluntary disruption

            - **Status:** Accepted (prototype corpus)
            - **Decision owner:** Platform Architecture
            - **Scope:** Production Kubernetes workloads where availability during voluntary disruption is required.

            ## Decision

            Workloads classified as availability-sensitive **MUST declare and maintain a disruption budget**.
            Tier-1 services MUST keep at least two pods available (`minAvailable: 2` or equivalent).

            ## Notes

            Prototype stand-in for org policy. Replace when importing real ADRs.
            """),
    },
    {
        "adr_id": "ADR-PLATFORM-002",
        "file": "SESSION-TTL.md",
        "title": "Limit session lifetime to 60 minutes",
        "domain": "identity",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-002-REQ-1",
                "kind": "numeric_max",
                "predicate": "session.ttl_seconds",
                "subject": "session",
                "limit": 3600,
                "decision": "Authenticated session lifetime MUST NOT exceed 60 minutes (3600 seconds).",
            },
        ],
        "body": textwrap.dedent("""\
            # ADR-PLATFORM-002 — Limit session lifetime to 60 minutes

            - **Status:** Accepted (prototype corpus)
            - **Decision owner:** Identity and Platform Architecture
            - **Scope:** Authenticated user and service sessions.

            ## Decision

            The maximum permitted lifetime of an authenticated session **MUST be 60 minutes**.
            Idle timeout alone does not satisfy this absolute maximum.

            ## Notes

            Prototype stand-in. Aligns with language-neutral SESSION-TTL policy used in demos.
            """),
    },
    {
        "adr_id": "ADR-PLATFORM-003",
        "file": "SESSION-IDLE-TIMEOUT.md",
        "title": "Idle session timeout maximum",
        "domain": "identity",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-003-REQ-1",
                "kind": "numeric_max",
                "predicate": "session.idle_timeout_seconds",
                "subject": "session",
                "limit": 900,
                "decision": "Idle session timeout MUST NOT exceed 15 minutes (900 seconds).",
            },
        ],
        "body": "# ADR-PLATFORM-003 — Idle session timeout\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nIdle session timeout MUST NOT exceed **15 minutes**.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-004",
        "file": "ADMIN-MFA.md",
        "title": "MFA required for administrative login",
        "domain": "identity",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-004-REQ-1",
                "kind": "boolean_required",
                "predicate": "identity.mfa.required",
                "subject": "admin-login",
                "decision": "Administrative interactive login MUST require MFA.",
            },
        ],
        "body": "# ADR-PLATFORM-004 — Admin MFA\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nMFA is required for administrative interactive login.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-005",
        "file": "PASSWORD-MIN-LENGTH.md",
        "title": "Password minimum length",
        "domain": "identity",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-005-REQ-1",
                "kind": "numeric_min",
                "predicate": "identity.password.min_length",
                "subject": "password-policy",
                "limit": 12,
                "decision": "Password minimum length MUST be at least 12 characters.",
            },
        ],
        "body": "# ADR-PLATFORM-005 — Password minimum length\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nPassword minimum length MUST be at least **12** characters.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-006",
        "file": "REFRESH-TOKEN-ROTATION.md",
        "title": "Refresh token rotation",
        "domain": "identity",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-006-REQ-1",
                "kind": "boolean_required",
                "predicate": "identity.refresh_token.rotation_enabled",
                "subject": "session",
                "decision": "Refresh tokens MUST use rotation on use.",
            },
        ],
        "body": "# ADR-PLATFORM-006 — Refresh token rotation\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nRefresh tokens use rotation on use.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-007",
        "file": "ENCRYPTION-AT-REST.md",
        "title": "Encryption at rest required",
        "domain": "security",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-007-REQ-1",
                "kind": "boolean_required",
                "predicate": "security.encryption_at_rest.enabled",
                "subject": "datastore",
                "decision": "Persistent datastores MUST enable encryption at rest.",
            },
        ],
        "body": "# ADR-PLATFORM-007 — Encryption at rest\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nEncryption at rest is required for persistent datastores.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-008",
        "file": "TLS-POLICY.md",
        "title": "Approved TLS policy",
        "domain": "security",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-008-REQ-1",
                "kind": "set_membership",
                "predicate": "security.tls_policy.id",
                "subject": "edge",
                "approved_set": ["tls-1-2-strict", "tls-1-3-only"],
                "decision": "Edge TLS policy MUST be one of tls-1-2-strict or tls-1-3-only.",
            },
        ],
        "body": "# ADR-PLATFORM-008 — TLS policy\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nApproved TLS policies: `tls-1-2-strict`, `tls-1-3-only`. Legacy SSL is forbidden.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-009",
        "file": "HSTS.md",
        "title": "HSTS enabled",
        "domain": "security",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-009-REQ-1",
                "kind": "boolean_required",
                "predicate": "security.hsts.enabled",
                "subject": "edge",
                "decision": "Public HTTPS edges MUST enable HSTS.",
            },
        ],
        "body": "# ADR-PLATFORM-009 — HSTS\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nHSTS is required on public HTTPS edges.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-010",
        "file": "API-RATE-LIMIT.md",
        "title": "API rate limiting",
        "domain": "api",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-010-REQ-1",
                "kind": "boolean_required",
                "predicate": "api.rate_limit.enabled",
                "subject": "public-api",
                "decision": "Public APIs MUST enforce rate limiting.",
            },
        ],
        "body": "# ADR-PLATFORM-010 — API rate limiting\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nRate limiting is enforced on public APIs.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-011",
        "file": "API-AUTH-MIDDLEWARE.md",
        "title": "API authentication middleware",
        "domain": "api",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-011-REQ-1",
                "kind": "boolean_required",
                "predicate": "api.auth_middleware.present",
                "subject": "public-api",
                "decision": "Public API routes MUST require authentication middleware.",
            },
        ],
        "body": "# ADR-PLATFORM-011 — API auth middleware\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nAll routes require auth via authentication middleware.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-012",
        "file": "OPENAPI-PUBLISHED.md",
        "title": "OpenAPI published for external APIs",
        "domain": "api",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-012-REQ-1",
                "kind": "boolean_required",
                "predicate": "api.openapi.published",
                "subject": "public-api",
                "decision": "Externally consumed APIs MUST publish an OpenAPI document.",
            },
        ],
        "body": "# ADR-PLATFORM-012 — OpenAPI published\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nOpenAPI document is published for externally consumed APIs.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-013",
        "file": "MIN-REPLICAS.md",
        "title": "Minimum deployment replicas",
        "domain": "reliability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-013-REQ-1",
                "kind": "numeric_min",
                "predicate": "kubernetes.deployment.replicas",
                "subject": "workload",
                "limit": 2,
                "decision": "Production deployments MUST run at least two replicas.",
            },
        ],
        "body": "# ADR-PLATFORM-013 — Minimum replicas\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nProduction deployments run with at least **2 replicas**.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-014",
        "file": "HEALTH-PROBES.md",
        "title": "Readiness and liveness probes",
        "domain": "reliability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-014-REQ-1",
                "kind": "boolean_required",
                "predicate": "kubernetes.readiness_probe.present",
                "subject": "workload",
                "decision": "Production pods MUST configure a readiness probe.",
            },
            {
                "requirement_id": "ADR-PLATFORM-014-REQ-2",
                "kind": "boolean_required",
                "predicate": "kubernetes.liveness_probe.present",
                "subject": "workload",
                "decision": "Production pods MUST configure a liveness probe.",
            },
        ],
        "body": "# ADR-PLATFORM-014 — Health probes\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nReadiness probe is configured and liveness probe is configured for production pods.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-015",
        "file": "MESSAGING-DLQ.md",
        "title": "Dead-letter queues required",
        "domain": "messaging",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-015-REQ-1",
                "kind": "boolean_required",
                "predicate": "messaging.dlq.present",
                "subject": "consumer",
                "decision": "Async consumers MUST configure a dead-letter queue (DLQ).",
            },
        ],
        "body": "# ADR-PLATFORM-015 — Dead-letter queues\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nA dead-letter queue (DLQ) is configured for async consumers.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-016",
        "file": "STRUCTURED-LOGGING.md",
        "title": "Structured JSON logging",
        "domain": "observability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-016-REQ-1",
                "kind": "boolean_required",
                "predicate": "observability.logging.structured_json",
                "subject": "service",
                "decision": "Services MUST emit structured JSON logs.",
            },
        ],
        "body": "# ADR-PLATFORM-016 — Structured JSON logging\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nStructured JSON logging is required.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-017",
        "file": "PII-LOG-SCRUBBING.md",
        "title": "PII scrubbing in logs",
        "domain": "observability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-017-REQ-1",
                "kind": "boolean_required",
                "predicate": "observability.logging.pii_scrubbing",
                "subject": "service",
                "decision": "Services MUST enable PII scrubbing in logs.",
            },
        ],
        "body": "# ADR-PLATFORM-017 — PII log scrubbing\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nPII scrubbing is enabled for application logs.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-018",
        "file": "SECRET-SCANNING.md",
        "title": "CI secret scanning",
        "domain": "cicd",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-018-REQ-1",
                "kind": "boolean_required",
                "predicate": "cicd.secret_scanning.enabled",
                "subject": "pipeline",
                "decision": "CI pipelines MUST enable secret scanning.",
            },
        ],
        "body": "# ADR-PLATFORM-018 — Secret scanning\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nSecret scanning is enabled in CI.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-019",
        "file": "BRANCH-PROTECTION-REVIEWS.md",
        "title": "Required pull request reviews",
        "domain": "cicd",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-019-REQ-1",
                "kind": "numeric_min",
                "predicate": "cicd.branch_protection.required_reviews",
                "subject": "default-branch",
                "limit": 1,
                "decision": "Default branch protection MUST require at least one review.",
            },
        ],
        "body": "# ADR-PLATFORM-019 — Required reviews\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nRequired reviews: at least **1** on the default branch.\n",
    },
    {
        "adr_id": "ADR-PLATFORM-020",
        "file": "NETWORK-POLICY.md",
        "title": "Kubernetes network policy",
        "domain": "reliability",
        "lifecycle_status": "accepted",
        "requirements": [
            {
                "requirement_id": "ADR-PLATFORM-020-REQ-1",
                "kind": "boolean_required",
                "predicate": "kubernetes.network_policy.present",
                "subject": "workload",
                "decision": "Production namespaces MUST configure network policies.",
            },
        ],
        "body": "# ADR-PLATFORM-020 — Network policy\n\n- **Status:** Accepted (prototype corpus)\n\n## Decision\n\nNetwork policies are configured for production namespaces.\n",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    preds_all = json.loads(PRED_SRC.read_text(encoding="utf-8"))["predicates"]
    needed: set[str] = set()
    for adr in CORPUS:
        for req in adr["requirements"]:
            needed.add(req["predicate"])
    missing = sorted(needed - set(preds_all))
    if missing:
        raise SystemExit(f"predicates missing from synthetic registry: {missing}")

    adrs_dir = ROOT / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)
    # Remove prior generated ADRs (keep directory)
    for old in adrs_dir.glob("*.md"):
        old.unlink()

    rows: list[dict] = []
    for adr in CORPUS:
        path = adrs_dir / adr["file"]
        path.write_text(adr["body"].rstrip() + "\n", encoding="utf-8")
        rev = sha256_file(path)
        for req in adr["requirements"]:
            row = {
                "adr_id": adr["adr_id"],
                "adr_revision": f"sha256:{rev}",
                "approval_state": "approved",
                "approved_by": "prototype-corpus-generator",
                "decision": req["decision"],
                "domain": adr["domain"],
                "kind": req["kind"],
                "label_status": "prototype_corpus_unadjudicated",
                "lifecycle_status": adr["lifecycle_status"],
                "predicate": req["predicate"],
                "requirement_id": req["requirement_id"],
                "applicability": {"domains": [adr["domain"]]},
                "source_span": {
                    "excerpt": req["decision"],
                    "path": f"adrs/{adr['file']}",
                },
                "subject": req["subject"],
                "title": adr["title"],
            }
            if "limit" in req:
                row["limit"] = req["limit"]
            if "approved_set" in req:
                row["approved_set"] = req["approved_set"]
            rows.append(row)

    slim = {"predicates": {k: preds_all[k] for k in sorted(needed)}}
    (ROOT / "predicates.json").write_text(
        json.dumps(slim, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    req_path = ROOT / "requirements.jsonl"
    with req_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    parts = []
    for rel in ["predicates.json", "requirements.jsonl"] + [
        f"adrs/{adr['file']}" for adr in CORPUS
    ]:
        parts.append(f"{rel}:{sha256_file(ROOT / rel)}")
    manifest_hash = sha256_bytes("\n".join(parts).encode("utf-8"))
    domains = sorted({adr["domain"] for adr in CORPUS})
    manifest = {
        "schema_version": "pathfinder-catalog-manifest-v1",
        "catalog_id": "platform-real-adr-v1",
        "catalog_mode": "real",
        "version": "1.0.0",
        "requirement_count": len(rows),
        "adr_count": len(CORPUS),
        "domains": domains,
        "manifest_sha256": manifest_hash,
        "label_status": "prototype_corpus_unadjudicated",
        "source_adrs": [f"adrs/{adr['file']}" for adr in CORPUS],
    }
    (ROOT / "catalog_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(CORPUS)} ADRs / {len(rows)} requirements; "
        f"manifest={manifest_hash[:12]}… domains={domains}"
    )


if __name__ == "__main__":
    main()
