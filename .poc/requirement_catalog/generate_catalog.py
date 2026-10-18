#!/usr/bin/env python3
"""Generate 100 synthetic ADRs, typed requirements, and predicate registry data.

Outputs are deterministic fixtures for the offline multi-ADR evaluation prototype.
They are synthetic and unadjudicated — not production policy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADR_DIR = ROOT / "adrs"
REQUIREMENTS_PATH = ROOT / "requirements.jsonl"
PREDICATES_PATH = ROOT / "predicates.json"
README_PATH = ROOT / "README.md"

# (domain, title, decision, kind, predicate, value_type, collector, params, subject_template)
# params: limit / approved_set / none depending on kind
SPECS: list[dict] = []


def add(domain: str, title: str, decision: str, kind: str, predicate: str, value_type: str,
        collector: str, *, subject: str = "service", **params) -> None:
    SPECS.append({
        "domain": domain,
        "title": title,
        "decision": decision,
        "kind": kind,
        "predicate": predicate,
        "value_type": value_type,
        "collector": collector,
        "subject": subject,
        "params": params,
    })


def build_specs() -> None:
    SPECS.clear()
    # Identity / session
    add("identity", "Session TTL maximum", "Authenticated session lifetime MUST NOT exceed 600 seconds.",
        "numeric_max", "session.ttl_seconds", "number", "structured_package", limit=600, subject="session")
    add("identity", "Idle timeout maximum", "Idle session timeout MUST NOT exceed 300 seconds.",
        "numeric_max", "session.idle_timeout_seconds", "number", "structured_package", limit=300, subject="session")
    add("identity", "MFA required for admins", "Administrative interactive login MUST require MFA.",
        "boolean_required", "identity.mfa.required", "boolean", "structured_package", subject="admin-login")
    add("identity", "Password min length", "Password minimum length MUST be at least 12 characters.",
        "numeric_min", "identity.password.min_length", "number", "structured_package", limit=12, subject="password-policy")
    add("identity", "Refresh token rotation", "Refresh tokens MUST use rotation on use.",
        "boolean_required", "identity.refresh_token.rotation_enabled", "boolean", "structured_package", subject="session")
    # Security / crypto
    add("security", "Encryption at rest", "Datastores holding customer data MUST enable encryption at rest.",
        "boolean_required", "security.encryption_at_rest.enabled", "boolean", "structured_package", subject="datastore")
    add("security", "TLS policy allowlist", "Edge TLS MUST use an approved policy identifier.",
        "set_membership", "security.tls_policy.id", "string", "structured_package",
        approved_set=["tls-1-2-strict", "tls-1-3-only"], subject="edge")
    add("security", "Secrets not in source", "Application secrets MUST NOT be hard-coded in source.",
        "dependency_forbidden", "security.secret_in_source.present", "boolean", "structured_package", subject="repository")
    add("security", "KMS key rotation", "Customer-managed keys MUST enable annual rotation.",
        "boolean_required", "security.kms.rotation_enabled", "boolean", "structured_package", subject="kms")
    add("security", "WAF enabled", "Public HTTP edges MUST enable a web application firewall.",
        "boolean_required", "security.waf.enabled", "boolean", "structured_package", subject="edge")
    # Privacy / data
    add("privacy", "PII logging ban", "Services MUST NOT log raw government ID or full payment PAN values.",
        "dependency_forbidden", "privacy.sensitive_log.present", "boolean", "structured_package", subject="logging")
    add("privacy", "Personal data retention max", "Personal data retention MUST NOT exceed 365 days without an approved exception.",
        "numeric_max", "privacy.data_retention_days", "number", "structured_package", limit=365, subject="data-store")
    add("privacy", "Consent recorded", "Marketing personalization MUST record consent state.",
        "boolean_required", "privacy.consent.recorded", "boolean", "structured_package", subject="marketing")
    add("privacy", "Right-to-delete API", "Customer data platforms MUST expose a deletion fulfillment path.",
        "boolean_required", "privacy.deletion_api.present", "boolean", "structured_package", subject="cdp")
    add("data", "Backup encryption", "Backups MUST be encrypted at rest.",
        "boolean_required", "data.backup.encryption_enabled", "boolean", "structured_package", subject="backup")
    add("data", "Backup retention minimum", "Critical system backups MUST retain at least 30 days.",
        "numeric_min", "data.backup.retention_days", "number", "structured_package", limit=30, subject="backup")
    add("data", "Schema migrations reviewed", "Destructive schema migrations MUST be explicitly flagged.",
        "boolean_required", "data.migration.destructive_flagged", "boolean", "structured_package", subject="migrations")
    add("data", "PII field classification", "Persisted customer profile fields MUST carry a data classification.",
        "boolean_required", "data.field.classification_present", "boolean", "structured_package", subject="profile-schema")
    # Reliability / kubernetes
    add("reliability", "Minimum replicas", "Production deployments MUST run at least three replicas.",
        "numeric_min", "kubernetes.deployment.replicas", "number", "structured_package", limit=3, subject="workload")
    add("reliability", "PDB present", "Disruption-sensitive workloads MUST have a matching PodDisruptionBudget.",
        "resource_present", "kubernetes.pod_disruption_budget.present", "boolean", "structured_package", subject="workload")
    add("reliability", "PDB min available", "PDBs for tier-1 services MUST keep at least two pods available.",
        "numeric_min", "kubernetes.pod_disruption_budget.min_available", "number", "structured_package", limit=2, subject="workload")
    add("reliability", "Readiness probe required", "HTTP services MUST define a readiness probe.",
        "boolean_required", "kubernetes.readiness_probe.present", "boolean", "structured_package", subject="workload")
    add("reliability", "Liveness probe required", "Long-running services MUST define a liveness probe.",
        "boolean_required", "kubernetes.liveness_probe.present", "boolean", "structured_package", subject="workload")
    add("reliability", "HPA present", "Variable-load production services MUST configure horizontal pod autoscaling.",
        "boolean_required", "kubernetes.hpa.present", "boolean", "structured_package", subject="workload")
    add("reliability", "Pod anti-affinity", "Tier-1 services MUST spread pods across nodes.",
        "boolean_required", "kubernetes.pod_anti_affinity.present", "boolean", "structured_package", subject="workload")
    # Networking
    add("networking", "NetworkPolicy present", "Namespaced production workloads MUST have a default-deny NetworkPolicy baseline.",
        "boolean_required", "kubernetes.network_policy.present", "boolean", "structured_package", subject="namespace")
    add("networking", "Ingress TLS required", "Public ingresses MUST terminate TLS.",
        "boolean_required", "kubernetes.ingress.tls_enabled", "boolean", "structured_package", subject="ingress")
    add("networking", "No public SSH", "Bastion access MUST NOT expose SSH to 0.0.0.0/0.",
        "dependency_forbidden", "network.ssh.public_exposure", "boolean", "structured_package", subject="bastion")
    add("networking", "Private subnet data tier", "Datastores MUST not attach public IPs.",
        "boolean_required", "network.datastore.private_only", "boolean", "structured_package", subject="datastore")
    add("networking", "Egress allowlist", "PCI workloads MUST use an egress allowlist.",
        "boolean_required", "network.egress.allowlist_enabled", "boolean", "structured_package", subject="pci-workload")
    # API
    add("api", "Auth middleware on public routes", "Public API routes MUST require authentication middleware.",
        "boolean_required", "api.auth_middleware.present", "boolean", "structured_package", subject="public-api")
    add("api", "Rate limiting", "Public APIs MUST enforce rate limiting.",
        "boolean_required", "api.rate_limit.enabled", "boolean", "structured_package", subject="public-api")
    add("api", "Request ID propagation", "Service APIs MUST propagate a request correlation ID.",
        "boolean_required", "api.request_id.propagated", "boolean", "structured_package", subject="service-api")
    add("api", "OpenAPI published", "Externally consumed APIs MUST publish an OpenAPI document.",
        "boolean_required", "api.openapi.published", "boolean", "structured_package", subject="public-api")
    add("api", "Breaking change policy", "Public APIs MUST NOT remove fields without a major version bump.",
        "boolean_required", "api.versioning.major_for_breaking", "boolean", "structured_package", subject="public-api")
    add("api", "Idempotency keys", "Payment mutation APIs MUST accept idempotency keys.",
        "boolean_required", "api.idempotency_key.supported", "boolean", "structured_package", subject="payments-api")
    # Cloud / IAM
    add("cloud", "No public object ACL", "Object storage holding customer data MUST NOT use public-read ACLs.",
        "dependency_forbidden", "cloud.object_storage.public_read", "boolean", "structured_package", subject="bucket")
    add("cloud", "Bucket versioning", "Critical document buckets MUST enable versioning.",
        "boolean_required", "cloud.object_storage.versioning_enabled", "boolean", "structured_package", subject="bucket")
    add("cloud", "IAM least privilege", "Runtime roles MUST NOT use AdministratorAccess-equivalent policies.",
        "dependency_forbidden", "cloud.iam.admin_equivalent", "boolean", "structured_package", subject="runtime-role")
    add("cloud", "CloudTrail enabled", "Accounts MUST enable control-plane audit logging.",
        "boolean_required", "cloud.audit_trail.enabled", "boolean", "structured_package", subject="account")
    add("cloud", "Root MFA", "Cloud account root users MUST have MFA enabled.",
        "boolean_required", "cloud.root.mfa_enabled", "boolean", "structured_package", subject="account")
    # Observability
    add("observability", "Structured JSON logs", "Services MUST emit structured JSON logs.",
        "boolean_required", "observability.logging.structured_json", "boolean", "structured_package", subject="service")
    add("observability", "Trace propagation", "Service-to-service calls MUST propagate trace context.",
        "boolean_required", "observability.tracing.context_propagated", "boolean", "structured_package", subject="service")
    add("observability", "RED metrics", "User-facing endpoints MUST expose rate/error/duration metrics.",
        "boolean_required", "observability.metrics.red_present", "boolean", "structured_package", subject="service")
    add("observability", "PII scrubbing in logs", "Log pipelines MUST scrub known PII fields.",
        "boolean_required", "observability.logging.pii_scrubbing", "boolean", "structured_package", subject="logging")
    add("observability", "Alert on error budget", "SLO services MUST alert when error budget burn is high.",
        "boolean_required", "observability.alerting.error_budget", "boolean", "structured_package", subject="slo-service")
    # CI/CD
    add("cicd", "No mutable latest tags in prod", "Production deploys MUST NOT use the mutable latest image tag.",
        "dependency_forbidden", "cicd.image.latest_tag", "boolean", "structured_package", subject="deployment")
    add("cicd", "Image signing required", "Production images MUST be signed.",
        "boolean_required", "cicd.image.signed", "boolean", "structured_package", subject="deployment")
    add("cicd", "Required PR reviews", "Default branch protection MUST require at least one review.",
        "numeric_min", "cicd.branch_protection.required_reviews", "number", "structured_package", limit=1, subject="repository")
    add("cicd", "CI required checks", "Merges MUST require green required status checks.",
        "boolean_required", "cicd.branch_protection.required_checks", "boolean", "structured_package", subject="repository")
    add("cicd", "Secrets scanning", "Repositories MUST enable secret scanning.",
        "boolean_required", "cicd.secret_scanning.enabled", "boolean", "structured_package", subject="repository")
    add("cicd", "SBOM published", "Released services MUST publish an SBOM artifact.",
        "boolean_required", "cicd.sbom.published", "boolean", "structured_package", subject="release")
    # Messaging / async
    add("messaging", "Dead-letter queue", "Durable consumers MUST configure a dead-letter queue.",
        "boolean_required", "messaging.dlq.present", "boolean", "structured_package", subject="consumer")
    add("messaging", "At-least-once handlers idempotent", "At-least-once consumers MUST be idempotent.",
        "boolean_required", "messaging.consumer.idempotent", "boolean", "structured_package", subject="consumer")
    add("messaging", "Poison message limit", "Consumers MUST bound retry attempts before DLQ.",
        "numeric_max", "messaging.consumer.max_retries", "number", "structured_package", limit=10, subject="consumer")
    add("messaging", "No sync call in request path to broker", "Request handlers MUST NOT block on unbounded broker publish retries.",
        "dependency_forbidden", "messaging.publish.blocking_unbounded", "boolean", "structured_package", subject="request-handler")
    add("messaging", "Outbox pattern for dual-write", "DB+message dual writes MUST use an outbox or equivalent.",
        "boolean_required", "messaging.outbox.present", "boolean", "structured_package", subject="write-path")
    # Frontend / client
    add("frontend", "CSP required", "Browser apps MUST set a Content-Security-Policy.",
        "boolean_required", "frontend.csp.present", "boolean", "structured_package", subject="web-app")
    add("frontend", "No secrets in client bundles", "Client bundles MUST NOT embed API secrets.",
        "dependency_forbidden", "frontend.secret_in_bundle.present", "boolean", "structured_package", subject="web-app")
    add("frontend", "Secure cookies", "Session cookies MUST set Secure and HttpOnly.",
        "boolean_required", "frontend.cookie.secure_httponly", "boolean", "structured_package", subject="web-app")
    add("frontend", "Dependency audit gate", "Frontend releases MUST fail on high/critical dependency advisories.",
        "boolean_required", "frontend.deps.audit_gate", "boolean", "structured_package", subject="web-app")
    # ML / AI
    add("ml", "Training data retention max", "Training datasets with personal data MUST NOT retain raw samples beyond 180 days.",
        "numeric_max", "ml.training_data.retention_days", "number", "structured_package", limit=180, subject="training-set")
    add("ml", "Model approval gate", "Production model promotions MUST record an approval record.",
        "boolean_required", "ml.model.approval_recorded", "boolean", "structured_package", subject="model-registry")
    add("ml", "Prompt/log redaction", "LLM gateway logs MUST redact secrets and raw PII.",
        "boolean_required", "ml.gateway.log_redaction", "boolean", "structured_package", subject="llm-gateway")
    add("ml", "Eval set before ship", "Model ships MUST attach an evaluation report reference.",
        "boolean_required", "ml.model.eval_report_present", "boolean", "structured_package", subject="model-registry")
    add("ml", "No unrestricted tool exec", "Agent runtimes MUST NOT allow unrestricted shell tool execution in production.",
        "dependency_forbidden", "ml.agent.unrestricted_shell", "boolean", "structured_package", subject="agent-runtime")
    # Compliance / audit
    add("compliance", "Audit log retention min", "Security audit logs MUST retain at least 365 days.",
        "numeric_min", "compliance.audit_log.retention_days", "number", "structured_package", limit=365, subject="audit-store")
    add("compliance", "Immutable audit store", "Security audit logs MUST use append-only or WORM storage controls.",
        "boolean_required", "compliance.audit_log.immutable", "boolean", "structured_package", subject="audit-store")
    add("compliance", "Access reviews quarterly", "Privileged access MUST be reviewed at least quarterly.",
        "boolean_required", "compliance.access_review.quarterly", "boolean", "structured_package", subject="iam")
    add("compliance", "Change tickets for prod", "Production config changes MUST reference a change ticket.",
        "boolean_required", "compliance.change_ticket.required", "boolean", "structured_package", subject="production")
    # Storage
    add("storage", "Disk encryption", "Block volumes MUST use encryption.",
        "boolean_required", "storage.volume.encryption_enabled", "boolean", "structured_package", subject="volume")
    add("storage", "Snapshot retention min", "Stateful production volumes MUST retain snapshots for at least 7 days.",
        "numeric_min", "storage.snapshot.retention_days", "number", "structured_package", limit=7, subject="volume")
    # Supply chain / deps
    add("supply-chain", "Forbidden dependency", "Services MUST NOT depend on the discontinued legacy-crypto package.",
        "dependency_forbidden", "supply_chain.dependency.legacy_crypto", "boolean", "structured_package", subject="service")
    add("supply-chain", "Pin dependency versions", "Application manifests MUST pin dependency versions.",
        "boolean_required", "supply_chain.dependencies.pinned", "boolean", "structured_package", subject="service")
    add("supply-chain", "License allowlist", "Released artifacts MUST use licenses from the approved set.",
        "set_membership", "supply_chain.license.id", "string", "structured_package",
        approved_set=["Apache-2.0", "MIT", "BSD-3-Clause"], subject="release")
    # Platform / tenancy
    add("platform", "Tenant isolation", "Multi-tenant query paths MUST enforce tenant predicates.",
        "boolean_required", "platform.tenant_isolation.enforced", "boolean", "structured_package", subject="query-path")
    add("platform", "No cross-tenant cache keys", "Caches MUST namespace keys by tenant.",
        "boolean_required", "platform.cache.tenant_namespaced", "boolean", "structured_package", subject="cache")
    # Expand to 100 with parameterized variants across domains
    extras = [
        ("security", "HSTS required", "Public HTTPS services MUST send HSTS.",
         "boolean_required", "security.hsts.enabled", "boolean", "edge"),
        ("security", "Certificate max validity", "Public certificates MUST NOT exceed 90 days validity.",
         "numeric_max", "security.certificate.validity_days", "number", "edge", {"limit": 90}),
        ("identity", "Session absolute clock", "Session absolute lifetime MUST be server-enforced.",
         "boolean_required", "session.server_enforced", "boolean", "session"),
        ("identity", "OAuth redirect allowlist", "OAuth clients MUST use an allowlisted redirect URI set.",
         "boolean_required", "identity.oauth.redirect_allowlist", "boolean", "oauth-client"),
        ("data", "Replica lag alert", "Primary/replica datastores MUST alert on lag above threshold.",
         "boolean_required", "data.replica.lag_alerting", "boolean", "datastore"),
        ("data", "Connection TLS", "Datastore clients MUST use TLS.",
         "boolean_required", "data.client.tls_required", "boolean", "datastore"),
        ("reliability", "Disruption budget max unavailable", "Tier-1 PDBs MUST set maxUnavailable to at most 1.",
         "numeric_max", "kubernetes.pod_disruption_budget.max_unavailable", "number", "workload", {"limit": 1}),
        ("reliability", "PodDisruptionBudget selector match", "PDB selectors MUST match the workload labels.",
         "boolean_required", "kubernetes.pod_disruption_budget.selector_matches", "boolean", "workload"),
        ("networking", "Service mesh mTLS", "Mesh-enrolled services MUST require mTLS.",
         "boolean_required", "network.mesh.mtls_required", "boolean", "service"),
        ("api", "Pagination required", "List endpoints returning unbounded collections MUST paginate.",
         "boolean_required", "api.pagination.present", "boolean", "public-api"),
        ("api", "Input validation", "Public write APIs MUST validate request schemas.",
         "boolean_required", "api.input_validation.present", "boolean", "public-api"),
        ("cloud", "Security group SSH restrict", "SSH security groups MUST NOT allow 0.0.0.0/0.",
         "dependency_forbidden", "cloud.security_group.ssh_open", "boolean", "security-group"),
        ("cloud", "RDS public access off", "Managed databases MUST disable public accessibility.",
         "boolean_required", "cloud.rds.public_access_disabled", "boolean", "datastore"),
        ("observability", "Log retention min", "Application logs MUST retain at least 30 days.",
         "numeric_min", "observability.logging.retention_days", "number", "logging", {"limit": 30}),
        ("observability", "On-call routing", "Production services MUST define on-call routing.",
         "boolean_required", "observability.oncall.defined", "boolean", "service"),
        ("cicd", "Artifact provenance", "Production deploys MUST attach build provenance.",
         "boolean_required", "cicd.provenance.present", "boolean", "deployment"),
        ("cicd", "Forbidden force push", "Default branches MUST deny force pushes.",
         "boolean_required", "cicd.branch_protection.deny_force_push", "boolean", "repository"),
        ("messaging", "Schema registry", "External event contracts MUST use a schema registry.",
         "boolean_required", "messaging.schema_registry.used", "boolean", "producer"),
        ("messaging", "PII in events banned", "Events MUST NOT carry raw government IDs.",
         "dependency_forbidden", "messaging.event.raw_gov_id", "boolean", "producer"),
        ("frontend", "SRI for third-party scripts", "Third-party scripts MUST use Subresource Integrity when loaded from CDN.",
         "boolean_required", "frontend.sri.required", "boolean", "web-app"),
        ("ml", "Dataset access logged", "Training dataset access MUST be audited.",
         "boolean_required", "ml.dataset.access_audited", "boolean", "training-set"),
        ("ml", "Human approval for high-risk tools", "High-risk agent tools MUST require human approval.",
         "boolean_required", "ml.agent.human_approval_high_risk", "boolean", "agent-runtime"),
        ("compliance", "Vendor DPIA recorded", "New personal-data processors MUST record a DPIA reference.",
         "boolean_required", "compliance.dpia.recorded", "boolean", "vendor"),
        ("compliance", "Encryption key access logged", "KMS key use for customer data MUST be logged.",
         "boolean_required", "compliance.kms_usage.logged", "boolean", "kms"),
        ("storage", "Object lock for legal hold", "Legal-hold buckets MUST support object lock.",
         "boolean_required", "storage.object_lock.enabled", "boolean", "bucket"),
        ("supply-chain", "Base image allowlist", "Runtime images MUST come from the approved base set.",
         "set_membership", "supply_chain.base_image.id", "string", "deployment",
         {"approved_set": ["distroless-base", "ubi9-minimal", "chainguard-static"]}),
        ("platform", "Feature flag kill switch", "Risky launches MUST have a kill-switch flag.",
         "boolean_required", "platform.feature_flag.kill_switch", "boolean", "service"),
        ("platform", "Config hot-reload bounded", "Hot-reloaded config MUST validate schema before apply.",
         "boolean_required", "platform.config.schema_validated", "boolean", "service"),
        ("security", "Dependency CVE gate", "Releases MUST block known critical CVEs in direct dependencies.",
         "boolean_required", "security.cve_gate.critical_blocked", "boolean", "release"),
        ("reliability", "Multi-AZ databaser", "Tier-1 databases MUST deploy across multiple availability zones.",
         "boolean_required", "reliability.datastore.multi_az", "boolean", "datastore"),
        ("networking", "DNSSEC for public zones", "External DNS zones MUST enable DNSSEC where supported.",
         "boolean_required", "network.dns.dnssec_enabled", "boolean", "public-zone"),
    ]
    for item in extras:
        domain, title, decision, kind, predicate, value_type, subject = item[:7]
        params = item[7] if len(item) > 7 else {}
        add(domain, title, decision, kind, predicate, value_type, "structured_package", subject=subject, **params)

    # Pad to exactly 100 with numbered reliability/security variants if short
    n = 1
    while len(SPECS) < 100:
        add(
            "reliability",
            f"Synthetic SLO burn alert variant {n}",
            f"Service SLO burn alerts MUST page when short-window burn exceeds factor {n + 1}.",
            "boolean_required",
            f"reliability.slo.burn_alert_v{n}",
            "boolean",
            "structured_package",
            subject="slo-service",
        )
        n += 1
    if len(SPECS) > 100:
        del SPECS[100:]


def adr_markdown(adr_id: str, spec: dict) -> str:
    return f"""# {adr_id}: {spec['title']}

## Status

Accepted for this synthetic evaluation catalog. Label status: synthetic_unadjudicated.

## Domain

{spec['domain']}

## Context

This control is a synthetic Pathfinder catalog entry used to exercise multi-requirement evaluation across technology domains. It is not an independently adjudicated enterprise policy.

## Decision

{spec['decision']}

## Typed requirement (catalog)

- kind: `{spec['kind']}`
- predicate: `{spec['predicate']}`
- subject template: `{spec['subject']}`

## Consequences

Missing or conflicting evidence MUST yield inconclusive results. Collectors bind by predicate capability, not by this ADR identifier.
"""


def main() -> None:
    build_specs()
    assert len(SPECS) == 100, len(SPECS)
    ADR_DIR.mkdir(parents=True, exist_ok=True)
    for path in ADR_DIR.glob("ADR-*.md"):
        path.unlink()

    predicates: dict[str, dict] = {}
    requirements: list[dict] = []
    for index, spec in enumerate(SPECS, start=101):
        adr_id = f"ADR-{index:03d}"
        adr_path = ADR_DIR / f"{adr_id}.md"
        body = adr_markdown(adr_id, spec)
        adr_path.write_text(body, encoding="utf-8")
        adr_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        kinds = {spec["kind"]}
        if spec["kind"] == "resource_present":
            kinds.add("boolean_required")
        existing = predicates.get(spec["predicate"])
        if existing:
            domains = set(existing.get("domains", []))
            domains.add(spec["domain"])
            existing["domains"] = sorted(domains)
            existing["compatible_kinds"] = sorted(set(existing["compatible_kinds"]) | kinds)
        else:
            predicates[spec["predicate"]] = {
                "value_type": spec["value_type"],
                "collector": spec["collector"],
                "description": spec["decision"],
                "compatible_kinds": sorted(kinds),
                "domains": [spec["domain"]],
            }

        requirement = {
            "requirement_id": f"{adr_id}-REQ-1",
            "adr_id": adr_id,
            "adr_revision": f"sha256:{adr_sha}",
            "domain": spec["domain"],
            "title": spec["title"],
            "kind": spec["kind"],
            "predicate": spec["predicate"],
            "subject": spec["subject"],
            "approval_state": "approved",
            "approved_by": "catalog-generator",
            "label_status": "synthetic_unadjudicated",
            "source_span": {"path": f"adrs/{adr_id}.md", "excerpt": spec["decision"]},
            "decision": spec["decision"],
        }
        requirement.update(spec["params"])
        requirements.append(requirement)

    # Ensure resource_present / boolean overlap for PDB predicate if present
    PREDICATES_PATH.write_text(
        json.dumps({"registry_version": "predicate-registry-v2", "predicates": predicates}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REQUIREMENTS_PATH.write_text("\n".join(json.dumps(item, sort_keys=True) for item in requirements) + "\n", encoding="utf-8")
    domain_counts: dict[str, int] = {}
    for item in requirements:
        domain_counts[item["domain"]] = domain_counts.get(item["domain"], 0) + 1
    README_PATH.write_text(
        f"""# Multi-ADR requirement catalog (synthetic)

This catalog contains **{len(requirements)}** synthetic ADRs (`ADR-101`–`ADR-200`) with approved typed requirements for offline multi-requirement evaluation.

- **Not** independently adjudicated production policy.
- Collectors bind by **predicate**, not ADR ID.
- Evaluate with `.poc/requirement_engine/evaluate_package.py`.

## Domain coverage

{chr(10).join(f'- `{domain}`: {count}' for domain, count in sorted(domain_counts.items()))}

## Files

- `adrs/` — synthetic ADR markdown
- `requirements.jsonl` — approved typed requirements
- `predicates.json` — registry seed loaded by the engine package
- `sample_packages/` — example tech-spec/code evidence packages
""",
        encoding="utf-8",
    )
    print(f"Wrote {len(requirements)} ADRs/requirements and {len(predicates)} predicates")


if __name__ == "__main__":
    main()
