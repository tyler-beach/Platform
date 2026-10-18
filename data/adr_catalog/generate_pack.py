#!/usr/bin/env python3
"""Generate a ~200-ADR prototype real catalog pack under data/adr_catalog/.

Sources:
  1) All 100 typed rows from .poc/requirement_catalog (standard engineering controls)
  2) 100 additional org-wide / enterprise-standard decisions with pack-local predicates

Stand-ins for a working prototype — replace with org ADRs later (see README.md).

  python3 data/adr_catalog/generate_pack.py
"""

from __future__ import annotations

import hashlib
import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SYN_PRED = REPO / ".poc" / "requirement_catalog" / "predicates.json"
SYN_REQ = REPO / ".poc" / "requirement_catalog" / "requirements.jsonl"

# Additional org-wide / enterprise ADRs beyond the engineering catalog.
# Each entry: title, domain, kind, predicate, subject, decision, optional limit/approved_set/forbidden.
ORG_WIDE: list[dict] = [
    # Change / SDLC governance
    ("Change advisory for production", "platform", "boolean_required", "change.cab.required", "production", "Production changes MUST go through change advisory (CAB) when risk is high."),
    ("Rollback plan required", "platform", "boolean_required", "change.rollback_plan.required", "production", "Production changes MUST include a documented rollback plan."),
    ("Maintenance window declared", "platform", "boolean_required", "change.maintenance_window.declared", "production", "Disruptive production changes MUST declare a maintenance window."),
    ("Feature flags for risky launches", "platform", "boolean_required", "change.feature_flag.required", "release", "High-risk launches MUST be gated behind a feature flag."),
    ("Post-incident review required", "platform", "boolean_required", "incident.postmortem.required", "sev1", "Sev-1 incidents MUST produce a blameless post-incident review."),
    ("Incident severity taxonomy", "platform", "boolean_required", "incident.severity.taxonomy_defined", "org", "The organization MUST define a severity taxonomy for incidents."),
    ("On-call coverage 24x7", "observability", "boolean_required", "ops.oncall.coverage_24x7", "production", "Production services MUST have 24x7 on-call coverage."),
    ("Runbook linked from alert", "observability", "boolean_required", "ops.alert.runbook_linked", "alert", "Paging alerts MUST link to a runbook."),
    ("Error budget policy defined", "reliability", "boolean_required", "sre.error_budget.policy_defined", "service", "SLI/SLO services MUST define an error-budget policy."),
    ("SLO dashboard published", "reliability", "boolean_required", "sre.slo.dashboard_published", "service", "Services with SLOs MUST publish an SLO dashboard."),
    # Data governance / privacy / retention
    ("Data classification labeling", "compliance", "boolean_required", "data.classification.label_required", "dataset", "Datasets containing personal or confidential data MUST carry a classification label."),
    ("Data owner assigned", "compliance", "boolean_required", "data.owner.assigned", "dataset", "Authoritative datasets MUST have an assigned data owner."),
    ("PII inventory maintained", "privacy", "boolean_required", "privacy.pii_inventory.maintained", "org", "Systems processing PII MUST maintain a PII inventory entry."),
    ("DPIA for high-risk processing", "privacy", "boolean_required", "privacy.dpia.required", "high-risk", "High-risk personal data processing MUST complete a DPIA."),
    ("Cross-border transfer controls", "privacy", "boolean_required", "privacy.cross_border.controls", "personal-data", "Cross-border personal data transfers MUST use approved transfer controls."),
    ("Right-to-erasure workflow", "privacy", "boolean_required", "privacy.erasure.workflow_present", "personal-data", "Customer personal data systems MUST support a right-to-erasure workflow."),
    ("Retention schedule documented", "compliance", "boolean_required", "records.retention.schedule_documented", "record-class", "Record classes MUST have a documented retention schedule."),
    ("Legal hold capability", "compliance", "boolean_required", "records.legal_hold.supported", "record-store", "Systems of record MUST support legal hold."),
    ("Backup tested periodically", "reliability", "boolean_required", "data.backup.restore_tested", "backup", "Critical backups MUST have periodic restore tests."),
    ("RPO maximum for tier-1", "reliability", "numeric_max", "data.backup.rpo_minutes", "tier1", "Tier-1 services MUST keep RPO at most 60 minutes.", {"limit": 60}),
    ("RTO maximum for tier-1", "reliability", "numeric_max", "data.backup.rto_minutes", "tier1", "Tier-1 services MUST keep RTO at most 240 minutes.", {"limit": 240}),
    # Identity / access / workforce
    ("Joiner-mover-leaver process", "identity", "boolean_required", "iam.jml.process_defined", "workforce", "Workforce access MUST follow a joiner-mover-leaver process."),
    ("Quarterly access review", "identity", "boolean_required", "iam.access_review.quarterly", "privileged", "Privileged access MUST undergo quarterly access review."),
    ("Privileged access just-in-time", "identity", "boolean_required", "iam.privileged.jit_required", "admin", "Standing admin access is forbidden; privileged access MUST be just-in-time."),
    ("Break-glass account monitored", "identity", "boolean_required", "iam.break_glass.monitored", "emergency", "Break-glass accounts MUST be monitored and alerted."),
    ("SSO for business apps", "identity", "boolean_required", "iam.sso.required", "business-app", "Business applications MUST use organization SSO."),
    ("SCIM provisioning", "identity", "boolean_required", "iam.scim.provisioning_enabled", "saas", "Enterprise SaaS with SCIM support MUST enable SCIM provisioning."),
    ("Contractor access time-bound", "identity", "boolean_required", "iam.contractor.time_bound", "contractor", "Contractor accounts MUST be time-bound with an expiry."),
    ("Password manager mandated", "identity", "boolean_required", "iam.password_manager.required", "workforce", "Workforce credentials MUST be stored in an approved password manager."),
    ("Hardware MFA for admins", "identity", "boolean_required", "iam.mfa.hardware_for_admins", "admin", "Administrators MUST use hardware-backed MFA."),
    ("Session recording for prod access", "security", "boolean_required", "security.prod_access.session_recorded", "production", "Interactive production access MUST be session-recorded."),
    # Security / vuln / endpoint
    ("Vulnerability SLA critical", "security", "numeric_max", "security.vuln.critical_fix_days", "asset", "Critical vulnerabilities MUST be remediated within 7 days.", {"limit": 7}),
    ("Vulnerability SLA high", "security", "numeric_max", "security.vuln.high_fix_days", "asset", "High vulnerabilities MUST be remediated within 30 days.", {"limit": 30}),
    ("Dependency scanning in CI", "cicd", "boolean_required", "cicd.dependency_scanning.enabled", "pipeline", "Application CI pipelines MUST enable dependency vulnerability scanning."),
    ("SAST enabled in CI", "cicd", "boolean_required", "cicd.sast.enabled", "pipeline", "Application CI pipelines MUST enable SAST."),
    ("Container image scanning", "cicd", "boolean_required", "cicd.image_scanning.enabled", "pipeline", "Container build pipelines MUST scan images before publish."),
    ("Endpoint disk encryption", "security", "boolean_required", "endpoint.disk_encryption.required", "laptop", "Corporate laptops MUST enable full-disk encryption."),
    ("Endpoint EDR deployed", "security", "boolean_required", "endpoint.edr.deployed", "laptop", "Corporate endpoints MUST run approved EDR."),
    ("Screen lock max minutes", "security", "numeric_max", "endpoint.screen_lock_minutes", "laptop", "Corporate endpoints MUST auto lock within 15 minutes.", {"limit": 15}),
    ("USB storage restricted", "security", "boolean_required", "endpoint.usb_storage.restricted", "laptop", "Removable USB storage MUST be restricted on corporate endpoints."),
    ("Email DLP enabled", "security", "boolean_required", "security.email_dlp.enabled", "email", "Corporate email MUST enable DLP for sensitive content."),
    ("Web proxy / CASB for SaaS", "security", "boolean_required", "security.casb.enabled", "saas", "Unmanaged SaaS access MUST be mediated by approved CASB/proxy controls."),
    # Cloud / network / infra standards
    ("Tagging standard enforced", "cloud", "boolean_required", "cloud.tags.standard_enforced", "resource", "Cloud resources MUST carry the org tagging standard (owner, env, cost-center)."),
    ("Nonprod data anonymized", "privacy", "boolean_required", "data.nonprod.anonymized", "nonprod", "Non-production environments MUST NOT use raw production PII without anonymization."),
    ("Public S3 blocked", "cloud", "boolean_required", "cloud.object_storage.public_blocked", "bucket", "Object storage public ACLs MUST be blocked at the org policy layer."),
    ("CloudTrail org trail", "cloud", "boolean_required", "cloud.audit.org_trail_enabled", "org", "The organization MUST enable an organization-wide audit trail."),
    ("GuardDuty or equivalent", "cloud", "boolean_required", "cloud.threat_detection.enabled", "account", "Cloud accounts MUST enable threat detection (e.g. GuardDuty or equivalent)."),
    ("Default VPC unused for prod", "networking", "boolean_required", "network.default_vpc.prod_forbidden", "production", "Production workloads MUST NOT run in the account default VPC."),
    ("Private subnets for data tiers", "networking", "boolean_required", "network.data_tier.private_subnet", "data-tier", "Data tiers MUST run in private subnets without public IPs."),
    ("WAF on public apps", "security", "boolean_required", "security.edge.waf_required", "public-app", "Internet-facing applications MUST sit behind a WAF."),
    ("DNS CAA records", "security", "boolean_required", "security.dns.caa_present", "public-zone", "Public DNS zones MUST publish CAA records."),
    ("Certificate inventory", "security", "boolean_required", "security.certificate.inventory_maintained", "org", "TLS certificates MUST be tracked in a certificate inventory."),
    # FinOps / vendor / procurement
    ("Cost center on every resource", "cloud", "boolean_required", "finops.cost_center.tagged", "resource", "Billable cloud resources MUST include a cost-center tag."),
    ("Budget alerts configured", "cloud", "boolean_required", "finops.budget.alerts_configured", "account", "Cloud accounts MUST configure budget alerts."),
    ("Idle resource review monthly", "cloud", "boolean_required", "finops.idle_review.monthly", "account", "Accounts MUST run a monthly idle-resource review."),
    ("Reserved/commit coverage target", "cloud", "numeric_min", "finops.commit.coverage_percent", "compute", "Steady-state compute MUST maintain at least 60% commit/reservation coverage.", {"limit": 60}),
    ("Vendor security questionnaire", "compliance", "boolean_required", "vendor.security.questionnaire_required", "vendor", "New vendors processing company or customer data MUST complete a security questionnaire."),
    ("DPA for personal data vendors", "privacy", "boolean_required", "vendor.dpa.required", "vendor", "Vendors processing personal data MUST have a signed DPA."),
    ("SOC2 or equivalent for critical vendors", "compliance", "boolean_required", "vendor.assurance.soc2_or_equivalent", "critical-vendor", "Critical vendors MUST provide SOC 2 or equivalent assurance."),
    ("Vendor offboarding checklist", "compliance", "boolean_required", "vendor.offboarding.checklist", "vendor", "Vendor offboarding MUST follow a checklist including access revocation and data return/destruction."),
    ("Software license compliance", "supply-chain", "boolean_required", "supply_chain.license.compliance_tracked", "application", "Applications MUST track open-source license compliance."),
    ("Approved SaaS catalog", "platform", "boolean_required", "saas.catalog.approved_only", "workforce", "Workforce SaaS MUST be limited to the approved catalog unless exceptioned."),
    # Product / API / frontend standards
    ("API deprecation notice days", "api", "numeric_min", "api.deprecation.notice_days", "public-api", "Public API deprecations MUST give at least 90 days notice.", {"limit": 90}),
    ("Breaking changes require version bump", "api", "boolean_required", "api.versioning.breaking_requires_major", "public-api", "Breaking public API changes MUST bump a major version."),
    ("Idempotency for payments", "api", "boolean_required", "api.payments.idempotency_required", "payments", "Payment mutation APIs MUST require idempotency keys."),
    ("CORS allowlist only", "frontend", "boolean_required", "frontend.cors.allowlist_only", "web", "Browser clients MUST use an explicit CORS allowlist (no `*`)."),
    ("Subresource integrity for CDN", "frontend", "boolean_required", "frontend.cdn.sri_required", "cdn", "Third-party CDN scripts MUST use Subresource Integrity."),
    ("Accessibility WCAG target", "frontend", "set_membership", "frontend.a11y.wcag_level", "web", "Customer-facing web apps MUST target WCAG 2.2 AA.", {"approved_set": ["wcag-2.2-aa", "wcag-2.1-aa"]}),
    ("Analytics consent gated", "privacy", "boolean_required", "privacy.analytics.consent_gated", "web", "Non-essential analytics MUST be consent-gated."),
    ("Mobile app certificate pinning", "security", "boolean_required", "mobile.tls.pinning_enabled", "mobile-app", "Mobile apps handling sensitive data MUST enable certificate pinning."),
    ("Crash reporting without PII", "privacy", "boolean_required", "mobile.crash.pii_scrubbed", "mobile-app", "Mobile crash reports MUST scrub PII before upload."),
    ("Store secrets out of app binaries", "security", "boolean_required", "mobile.secrets.not_in_binary", "mobile-app", "Mobile app binaries MUST NOT embed long-lived API secrets."),
    # Messaging / ML / data platforms
    ("PII forbidden in event payloads", "messaging", "boolean_required", "messaging.event.pii_forbidden", "event", "Domain events MUST NOT carry raw government IDs or full payment PANs."),
    ("Schema compatibility checks", "messaging", "boolean_required", "messaging.schema.compatibility_checked", "topic", "Evolving event schemas MUST pass compatibility checks in CI."),
    ("Poison message quarantine", "messaging", "boolean_required", "messaging.poison.quarantine_enabled", "consumer", "Consumers MUST quarantine poison messages after retry exhaustion."),
    ("ML training data lineage", "ml", "boolean_required", "ml.training.lineage_recorded", "model", "Production models MUST record training data lineage."),
    ("ML model approval gate", "ml", "boolean_required", "ml.model.approval_required", "model", "Production model promotion MUST pass an approval gate."),
    ("ML prompt injection defenses", "ml", "boolean_required", "ml.llm.prompt_injection_controls", "llm-app", "LLM applications MUST implement prompt-injection controls for untrusted input."),
    ("ML output filtering", "ml", "boolean_required", "ml.llm.output_filtered", "llm-app", "LLM applications MUST filter outputs for secrets and disallowed content classes."),
    ("Feature store access controlled", "ml", "boolean_required", "ml.feature_store.access_controlled", "feature-store", "Feature stores MUST enforce authenticated, authorized access."),
    ("Notebook secrets from vault", "ml", "boolean_required", "ml.notebook.secrets_from_vault", "notebook", "Notebooks MUST load secrets from a vault, not plaintext cells."),
    ("Batch job idempotency", "data", "boolean_required", "data.batch.idempotent", "job", "Scheduled batch jobs that mutate state MUST be idempotent."),
    # Compliance / audit / business continuity
    ("Audit log immutable store", "compliance", "boolean_required", "compliance.audit_log.immutable_store", "audit", "Security audit logs MUST be written to an immutable or WORM-capable store."),
    ("Audit log retention years", "compliance", "numeric_min", "compliance.audit_log.retention_years", "audit", "Security audit logs MUST be retained at least 1 year.", {"limit": 1}),
    ("Business continuity plan", "reliability", "boolean_required", "bc.plan.documented", "org", "The organization MUST maintain a business continuity plan."),
    ("Disaster recovery tested yearly", "reliability", "boolean_required", "dr.test.yearly", "tier1", "Tier-1 DR plans MUST be tested at least yearly."),
    ("Regulatory mapping owned", "compliance", "boolean_required", "compliance.framework.mapping_owned", "org", "Applicable regulatory frameworks MUST have a named control-mapping owner."),
    ("Customer notification SLA hours", "privacy", "numeric_max", "privacy.breach.notify_hours", "breach", "Confirmed personal-data breaches MUST begin customer/regulator notification workflows within 72 hours.", {"limit": 72}),
    ("Encryption key rotation days", "security", "numeric_max", "security.kms.rotation_days", "key", "Symmetric data keys MUST rotate at least every 365 days.", {"limit": 365}),
    ("Secrets max age days", "security", "numeric_max", "security.secrets.max_age_days", "secret", "Long-lived application secrets MUST rotate within 90 days.", {"limit": 90}),
    # Architecture / platform conventions
    ("Service tier classification", "platform", "boolean_required", "architecture.service_tier.assigned", "service", "Production services MUST be assigned a service tier (0–3)."),
    ("Architecture review for tier-0/1", "platform", "boolean_required", "architecture.review.required_tier01", "service", "Tier-0/1 services MUST pass architecture review before major launches."),
    ("ADR required for cross-cutting decisions", "platform", "boolean_required", "architecture.adr.required", "cross-cutting", "Cross-cutting technical decisions MUST be recorded as ADRs."),
    ("Multi-tenant isolation tested", "platform", "boolean_required", "architecture.tenant_isolation.tested", "multi-tenant", "Multi-tenant systems MUST have automated tenant-isolation tests."),
    ("Dependency on deprecated runtime forbidden", "supply-chain", "dependency_forbidden", "runtime.version.deprecated_forbidden", "service", "Services MUST NOT deploy on deprecated language runtimes."),
    ("Internal package registry only", "supply-chain", "boolean_required", "supply_chain.registry.internal_required", "build", "Builds MUST pull private packages from the internal registry."),
    ("Artifact provenance attestation", "cicd", "boolean_required", "cicd.provenance.attestation_required", "release", "Production releases MUST publish build provenance attestations."),
    ("Prod deploy requires approval", "cicd", "boolean_required", "cicd.prod.approval_required", "production", "Production deployments MUST require a human approval gate."),
    ("Infrastructure as code required", "cloud", "boolean_required", "cloud.iac.required", "infrastructure", "Production infrastructure MUST be managed as code."),
    ("Drift detection enabled", "cloud", "boolean_required", "cloud.iac.drift_detection", "infrastructure", "IaC-managed environments MUST enable drift detection."),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def slug(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return s[:80] or "adr"


def adr_markdown(adr_id: str, title: str, domain: str, decision: str, status: str = "Accepted (prototype corpus)") -> str:
    return textwrap.dedent(
        f"""\
        # {adr_id} — {title}

        - **Status:** {status}
        - **Domain:** {domain}
        - **Decision owner:** Platform Architecture (prototype)
        - **Scope:** Organization-wide standard unless a documented exception exists.

        ## Decision

        {decision}

        ## Notes

        Prototype corpus stand-in for org policy. Replace when importing real ADRs.
        """
    )


def load_synthetic() -> tuple[dict, list[dict]]:
    preds = json.loads(SYN_PRED.read_text(encoding="utf-8"))["predicates"]
    rows = []
    for line in SYN_REQ.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return preds, rows


def build_org_predicates() -> dict:
    """Pack-local predicates for the extra 100 org-wide ADRs."""
    out = {}
    for item in ORG_WIDE:
        title, domain, kind, predicate, subject, decision = item[:6]
        extra = item[6] if len(item) > 6 else {}
        value_type = {
            "boolean_required": "boolean",
            "resource_present": "boolean",
            "numeric_max": "number",
            "numeric_min": "number",
            "set_membership": "string",
            "dependency_forbidden": "string",
        }[kind]
        out[predicate] = {
            "collector": "structured_package",
            "compatible_kinds": [kind],
            "description": decision,
            "domains": [domain],
            "value_type": value_type,
            "subject_hint": subject,
        }
        if "limit" in extra:
            out[predicate]["example_limit"] = extra["limit"]
    return out


def main() -> None:
    syn_preds, syn_rows = load_synthetic()
    if len(syn_rows) != 100:
        raise SystemExit(f"expected 100 synthetic requirements, got {len(syn_rows)}")
    if len(ORG_WIDE) != 100:
        raise SystemExit(f"expected 100 ORG_WIDE ADRs, got {len(ORG_WIDE)}")

    org_preds = build_org_predicates()
    all_preds = dict(syn_preds)
    overlap = set(org_preds) & set(all_preds)
    if overlap:
        raise SystemExit(f"ORG_WIDE predicates collide with synthetic registry: {sorted(overlap)[:10]}")
    all_preds.update(org_preds)

    adrs_dir = ROOT / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)
    for old in adrs_dir.glob("*.md"):
        old.unlink()

    corpus: list[dict] = []
    used_predicates: set[str] = set()

    # Block A: engineering controls from synthetic catalog → ADR-PLATFORM-001..100
    for idx, row in enumerate(sorted(syn_rows, key=lambda r: r["adr_id"]), start=1):
        adr_id = f"ADR-PLATFORM-{idx:03d}"
        title = row.get("title") or row["predicate"]
        domain = row["domain"]
        decision = row["decision"]
        filename = f"{adr_id}-{slug(title)}.md"
        body = adr_markdown(adr_id, title, domain, decision)
        path = adrs_dir / filename
        path.write_text(body, encoding="utf-8")
        rev = sha256_file(path)
        req = {
            "adr_id": adr_id,
            "adr_revision": f"sha256:{rev}",
            "approval_state": "approved",
            "approved_by": "prototype-corpus-generator",
            "decision": decision,
            "domain": domain,
            "kind": row["kind"],
            "label_status": "prototype_corpus_unadjudicated",
            "lifecycle_status": "accepted",
            "predicate": row["predicate"],
            "requirement_id": f"{adr_id}-REQ-1",
            "applicability": {"domains": [domain]},
            "source_span": {"excerpt": decision, "path": f"adrs/{filename}"},
            "subject": row["subject"],
            "title": title,
        }
        if "limit" in row:
            req["limit"] = row["limit"]
        if "approved_set" in row:
            req["approved_set"] = row["approved_set"]
        corpus.append({"file": filename, "domain": domain, "row": req})
        used_predicates.add(row["predicate"])

    # Block B: org-wide standards → ADR-PLATFORM-101..200
    for offset, item in enumerate(ORG_WIDE, start=101):
        title, domain, kind, predicate, subject, decision = item[:6]
        extra = item[6] if len(item) > 6 else {}
        adr_id = f"ADR-PLATFORM-{offset:03d}"
        filename = f"{adr_id}-{slug(title)}.md"
        body = adr_markdown(adr_id, title, domain, decision)
        path = adrs_dir / filename
        path.write_text(body, encoding="utf-8")
        rev = sha256_file(path)
        req = {
            "adr_id": adr_id,
            "adr_revision": f"sha256:{rev}",
            "approval_state": "approved",
            "approved_by": "prototype-corpus-generator",
            "decision": decision,
            "domain": domain,
            "kind": kind,
            "label_status": "prototype_corpus_unadjudicated",
            "lifecycle_status": "accepted",
            "predicate": predicate,
            "requirement_id": f"{adr_id}-REQ-1",
            "applicability": {"domains": [domain]},
            "source_span": {"excerpt": decision, "path": f"adrs/{filename}"},
            "subject": subject,
            "title": title,
        }
        if "limit" in extra:
            req["limit"] = extra["limit"]
        if "approved_set" in extra:
            req["approved_set"] = extra["approved_set"]
        corpus.append({"file": filename, "domain": domain, "row": req})
        used_predicates.add(predicate)

    if len(corpus) != 200:
        raise SystemExit(f"expected 200 ADRs, got {len(corpus)}")

    # dependency_forbidden in engine - check what fields it needs
    slim = {"predicates": {k: all_preds[k] for k in sorted(used_predicates)}}
    # Ensure every used predicate exists
    missing = sorted(used_predicates - set(all_preds))
    if missing:
        raise SystemExit(f"missing predicates: {missing[:20]}")

    (ROOT / "predicates.json").write_text(
        json.dumps(slim, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    req_path = ROOT / "requirements.jsonl"
    with req_path.open("w", encoding="utf-8") as fh:
        for item in corpus:
            fh.write(json.dumps(item["row"], sort_keys=True, separators=(",", ":")) + "\n")

    parts = ["predicates.json:" + sha256_file(ROOT / "predicates.json"), "requirements.jsonl:" + sha256_file(req_path)]
    for item in corpus:
        parts.append(f"adrs/{item['file']}:" + sha256_file(adrs_dir / item["file"]))
    manifest_hash = sha256_bytes("\n".join(parts).encode("utf-8"))
    domains = sorted({item["domain"] for item in corpus})
    manifest = {
        "schema_version": "pathfinder-catalog-manifest-v1",
        "catalog_id": "platform-real-adr-v1",
        "catalog_mode": "real",
        "version": "1.1.0",
        "requirement_count": len(corpus),
        "adr_count": len(corpus),
        "domains": domains,
        "manifest_sha256": manifest_hash,
        "label_status": "prototype_corpus_unadjudicated",
        "composition": {
            "engineering_controls_from_synthetic": 100,
            "org_wide_enterprise_standards": 100,
        },
        "source_adrs": [f"adrs/{item['file']}" for item in corpus],
    }
    (ROOT / "catalog_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(corpus)} ADRs / {len(corpus)} requirements; "
        f"predicates={len(slim['predicates'])}; domains={len(domains)}; "
        f"manifest={manifest_hash[:12]}…"
    )


if __name__ == "__main__":
    main()
