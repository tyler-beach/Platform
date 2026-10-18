#!/usr/bin/env python3
"""Fail-closed extraction of typed catalog observations from pasted tech-spec/code.

Deterministic heuristics + Python AST only. Never calls a model. Never invents
negative presence observations from silence. Conflicting values for the same
(predicate, subject) drop all candidates for that key.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import catalog

EXTRACTOR_ID = "paste_heuristic_v1"
EXTRACTOR_VERSION = "paste-heuristic-v1"

# Presence/forbidden predicates that may only be emitted as True when a match is found.
TRUE_ONLY_PREDICATES = frozenset({
    "security.secret_in_source.present",
    "privacy.sensitive_log.present",
    "frontend.secret_in_bundle.present",
    "messaging.event.raw_gov_id",
    "cicd.image.latest_tag",
    "cloud.security_group.ssh_open",
    "cloud.iam.admin_equivalent",
    "cloud.object_storage.public_read",
    "ml.agent.unrestricted_shell",
    "network.ssh.public_exposure",
    "supply_chain.dependency.legacy_crypto",
})

SECRET_LITERAL_RE = re.compile(
    r"""(?ix)
    (?:
      (?:api[_-]?key|secret|password|token|private[_-]?key|access[_-]?key)
      \s*[=:]\s*
      ["']([^"']{8,})["']
    )
    |
    (?:
      ["'](
        sk[-_]live[-_][A-Za-z0-9]{8,}
        | sk[-_]test[-_][A-Za-z0-9]{8,}
        | AKIA[0-9A-Z]{16}
        | gh[pousr]_[A-Za-z0-9]{20,}
      )["']
    )
    """
)

SENSITIVE_LOG_RE = re.compile(
    r"(?i)\b(log|logger|print|fmt\.Print|slog)\w*\s*\([^)]*\b(pan|ssn|social\s*security|credit\s*card|cvv|password)\b",
)

TLS_POLICY_RE = re.compile(r"\b(tls-1-2-strict|tls-1-3-only|legacy-ssl)\b", re.I)
LICENSE_RE = re.compile(r"\b(Apache-2\.0|MIT|BSD-3-Clause)\b")


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _subjects() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in catalog.load_requirements():
        mapping[row["predicate"]] = row["subject"]
    return mapping


def _line_span(text: str, start: int, end: int) -> dict[str, Any]:
    line = text.count("\n", 0, start) + 1
    excerpt = text[start:end]
    return {
        "kind": "paste_span",
        "line": line,
        "start": start,
        "end": end,
        "excerpt_sha256": _sha(excerpt),
        "extractor": EXTRACTOR_ID,
        "extractor_version": EXTRACTOR_VERSION,
    }


def _candidate(
    *,
    predicate: str,
    value: Any,
    artifact: dict[str, Any],
    text: str,
    start: int,
    end: int,
    subjects: dict[str, str],
    evidence_prefix: str,
) -> dict[str, Any] | None:
    subject = subjects.get(predicate)
    if not subject:
        return None
    if predicate in TRUE_ONLY_PREDICATES and value is not True:
        return None
    digest = artifact["sha256"]
    return {
        "evidence_id": f"{evidence_prefix}-{predicate.replace('.', '_')}-{start}",
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "artifact_id": artifact["artifact_id"],
        "revision": artifact["revision"],
        "path": artifact["path"],
        "source_sha256": digest,
        "locator": _line_span(text, start, end),
    }


def _to_seconds(amount: float, unit: str) -> int:
    unit = unit.lower().rstrip("s")
    if unit.startswith("second"):
        return int(amount)
    if unit.startswith("minute"):
        return int(amount * 60)
    if unit.startswith("hour"):
        return int(amount * 3600)
    if unit.startswith("day"):
        return int(amount * 86400)
    raise ValueError(f"unsupported unit {unit}")


def _artifacts_from_package(package: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    tech = package.get("tech_spec")
    if isinstance(tech, dict) and isinstance(tech.get("content"), str) and tech["content"].strip():
        content = tech["content"]
        digest = tech.get("sha256") or _sha(content)
        out.append({
            "artifact_id": tech.get("artifact_id", "tech_spec"),
            "path": tech.get("path", "issue/tech-spec.md"),
            "revision": tech.get("revision", f"sha256:{digest}"),
            "sha256": digest,
            "content": content,
            "language": "markdown",
        })
    for index, block in enumerate(package.get("code") or []):
        if not isinstance(block, dict) or not isinstance(block.get("content"), str):
            continue
        content = block["content"]
        if not content.strip():
            continue
        digest = block.get("sha256") or _sha(content)
        path = block.get("path", f"issue/sample-code-{index}.txt")
        out.append({
            "artifact_id": block.get("artifact_id", f"code-{index}"),
            "path": path,
            "revision": block.get("revision", f"sha256:{digest}"),
            "sha256": digest,
            "content": content,
            "language": _detect_language(path, content),
        })
    return out


def _detect_language(path: str, content: str) -> str:
    lower = path.lower()
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".go"):
        return "go"
    if lower.endswith((".md", ".markdown", ".txt")):
        return "markdown"
    if "package main" in content or re.search(r"\bfunc\s+\w+\s*\(", content):
        return "go"
    if re.search(r"^\s*(def|class|import|from)\s+", content, re.M) or "async def" in content:
        return "python"
    if content.lstrip().startswith("{") or content.lstrip().startswith("["):
        return "json"
    return "markdown"


def extract_markdown(text: str, artifact: dict[str, Any], subjects: dict[str, str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    def add(predicate: str, value: Any, match: re.Match[str]) -> None:
        item = _candidate(
            predicate=predicate,
            value=value,
            artifact=artifact,
            text=text,
            start=match.start(),
            end=match.end(),
            subjects=subjects,
            evidence_prefix="EXT-md",
        )
        if item:
            hits.append(item)

    # Session TTL / idle timeout with units.
    for pred, patterns in (
        ("session.ttl_seconds", [
            r"(?i)sessions?\s+(?:expire|ttl|lifetime|timeout)\w*\s*(?:after|of|:)?\s*(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?)",
            r"(?i)(?:absolute\s+)?(?:session\s+)?ttl\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?)",
            r"(?i)session(?:s)?\s+(?:are\s+)?valid\s+for\s+(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?)",
        ]),
        ("session.idle_timeout_seconds", [
            r"(?i)idle\s+(?:session\s+)?(?:timeout|expire\w*)\s*(?:after|of|:)?\s*(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?)",
        ]),
    ):
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                try:
                    add(pred, _to_seconds(float(match.group(1)), match.group(2)), match)
                except ValueError:
                    continue

    numeric_patterns: list[tuple[str, str, Any]] = [
        ("kubernetes.deployment.replicas", r"(?i)\breplicas?\s*[:=]\s*(\d+)\b", int),
        ("kubernetes.deployment.replicas", r"(?i)\b(?:run|deploy(?:ed|ment)?)\s+(?:with\s+)?(\d+)\s+replicas?\b", int),
        ("messaging.consumer.max_retries", r"(?i)\b(?:max(?:imum)?\s+)?retries?\s*[:=]\s*(\d+)\b", int),
        ("messaging.consumer.max_retries", r"(?i)\bconsumer\s+max\s+retries?\s*[:=]?\s*(\d+)\b", int),
        ("identity.password.min_length", r"(?i)\bpassword\s+(?:minimum\s+)?(?:length|min)\s*[:=]?\s*(\d+)\b", int),
        ("observability.logging.retention_days", r"(?i)\blog(?:ging)?\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("privacy.data_retention_days", r"(?i)\bdata\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("compliance.audit_log.retention_days", r"(?i)\baudit\s+log\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("data.backup.retention_days", r"(?i)\bbackup\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("storage.snapshot.retention_days", r"(?i)\bsnapshot\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("security.certificate.validity_days", r"(?i)\bcertificate\s+validity\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("ml.training_data.retention_days", r"(?i)\btraining\s+data\s+retention\s*[:=]?\s*(\d+)\s*days?\b", int),
        ("kubernetes.pod_disruption_budget.max_unavailable", r"(?i)\bmaxUnavailable\s*[:=]\s*(\d+)\b", int),
        ("kubernetes.pod_disruption_budget.min_available", r"(?i)\bminAvailable\s*[:=]\s*(\d+)\b", int),
        ("cicd.branch_protection.required_reviews", r"(?i)\brequired\s+reviews?\s*[:=]?\s*(\d+)\b", int),
    ]
    for predicate, pattern, cast in numeric_patterns:
        for match in re.finditer(pattern, text):
            add(predicate, cast(match.group(1)), match)

    bool_true = [
        ("security.encryption_at_rest.enabled", r"(?i)\bencryption\s+at\s+rest\s+(?:is\s+)?(?:enabled|on|required)\b"),
        ("security.encryption_at_rest.enabled", r"(?i)\benable(?:s|d)?\s+encryption\s+at\s+rest\b"),
        ("storage.volume.encryption_enabled", r"(?i)\bvolume\s+encryption\s+(?:is\s+)?(?:enabled|on|required)\b"),
        ("data.backup.encryption_enabled", r"(?i)\bbackup\s+encryption\s+(?:is\s+)?(?:enabled|on|required)\b"),
        ("kubernetes.readiness_probe.present", r"(?i)\breadiness\s+probe\s+(?:is\s+)?(?:configured|present|enabled)\b"),
        ("kubernetes.liveness_probe.present", r"(?i)\bliveness\s+probe\s+(?:is\s+)?(?:configured|present|enabled)\b"),
        ("kubernetes.pod_disruption_budget.present", r"(?i)\b(?:pod\s+disruption\s+budget|PDB)\s+(?:is\s+)?(?:configured|present|required|defined)\b"),
        ("kubernetes.hpa.present", r"(?i)\b(?:horizontal\s+pod\s+autoscaler|HPA)\s+(?:is\s+)?(?:configured|present|enabled)\b"),
        ("kubernetes.network_policy.present", r"(?i)\bnetwork\s+polic(?:y|ies)\s+(?:is|are)\s+(?:configured|present|enabled)\b"),
        ("kubernetes.ingress.tls_enabled", r"(?i)\bingress\s+tls\s+(?:is\s+)?(?:enabled|required|terminated)\b"),
        ("messaging.dlq.present", r"(?i)\b(?:dead[- ]letter\s+queue|DLQ)\s+(?:is\s+)?(?:configured|present|enabled|used)\b"),
        ("messaging.outbox.present", r"(?i)\boutbox\s+(?:pattern\s+)?(?:is\s+)?(?:used|present|configured)\b"),
        ("messaging.consumer.idempotent", r"(?i)\b(?:consumers?\s+are\s+idempotent|idempotent\s+consumers?)\b"),
        ("messaging.schema_registry.used", r"(?i)\bschema\s+registry\s+(?:is\s+)?(?:used|required|enabled)\b"),
        ("api.rate_limit.enabled", r"(?i)\brate\s+limit(?:ing)?\s+(?:is\s+)?(?:enabled|enforced|required)\b"),
        ("api.auth_middleware.present", r"(?i)\b(?:auth(?:entication)?\s+middleware|all\s+routes\s+require\s+auth)\b"),
        ("api.input_validation.present", r"(?i)\b(?:request|input)\s+validation\s+(?:is\s+)?(?:enabled|required|enforced)\b"),
        ("api.pagination.present", r"(?i)\b(?:list\s+)?(?:endpoints?\s+)?paginat(?:e|ion)\b"),
        ("api.openapi.published", r"(?i)\bopenapi\s+(?:spec|document)?\s+(?:is\s+)?(?:published|available)\b"),
        ("api.request_id.propagated", r"(?i)\brequest[- ]id\s+(?:is\s+)?(?:propagated|required)\b"),
        ("identity.mfa.required", r"(?i)\b(?:mfa|multi[- ]factor)\s+(?:is\s+)?(?:required|enforced|mandatory)\b"),
        ("identity.refresh_token.rotation_enabled", r"(?i)\brefresh\s+tokens?\s+(?:use\s+)?rotation\b"),
        ("session.server_enforced", r"(?i)\bsessions?\s+(?:are\s+)?server[- ](?:side\s+)?enforced\b"),
        ("security.hsts.enabled", r"(?i)\bhsts\s+(?:is\s+)?(?:enabled|required)\b"),
        ("security.waf.enabled", r"(?i)\bwaf\s+(?:is\s+)?(?:enabled|required|deployed)\b"),
        ("security.kms.rotation_enabled", r"(?i)\bkms\s+(?:key\s+)?rotation\s+(?:is\s+)?(?:enabled|required)\b"),
        ("observability.logging.structured_json", r"(?i)\bstructured\s+json\s+log(?:ging|s)?\b"),
        ("observability.logging.pii_scrubbing", r"(?i)\b(?:pii|sensitive)\s+(?:scrubbing|redaction)\s+(?:is\s+)?(?:enabled|required)\b"),
        ("observability.tracing.context_propagated", r"(?i)\b(?:trace|tracing)\s+context\s+(?:is\s+)?propagated\b"),
        ("observability.oncall.defined", r"(?i)\bon[- ]call\s+(?:rotation\s+)?(?:is\s+)?(?:defined|configured)\b"),
        ("cicd.secret_scanning.enabled", r"(?i)\bsecret\s+scanning\s+(?:is\s+)?(?:enabled|required)\b"),
        ("cicd.branch_protection.deny_force_push", r"(?i)\bforce\s+push(?:es)?\s+(?:are\s+)?denied\b"),
        ("cicd.image.signed", r"(?i)\b(?:container\s+)?images?\s+(?:are\s+)?signed\b"),
        ("cicd.sbom.published", r"(?i)\bsbom\s+(?:is\s+)?(?:published|required)\b"),
        ("data.client.tls_required", r"(?i)\b(?:database|datastore)\s+client\s+tls\s+(?:is\s+)?required\b"),
        ("cloud.rds.public_access_disabled", r"(?i)\b(?:rds|database)\s+public\s+access\s+(?:is\s+)?disabled\b"),
        ("cloud.object_storage.versioning_enabled", r"(?i)\b(?:bucket|object\s+storage)\s+versioning\s+(?:is\s+)?(?:enabled|on)\b"),
        ("cloud.audit_trail.enabled", r"(?i)\b(?:cloud\s+)?audit\s+trail\s+(?:is\s+)?(?:enabled|on)\b"),
        ("cloud.root.mfa_enabled", r"(?i)\broot\s+(?:user\s+)?mfa\s+(?:is\s+)?(?:enabled|required)\b"),
        ("privacy.deletion_api.present", r"(?i)\bdeletion\s+api\s+(?:is\s+)?(?:present|available|implemented)\b"),
        ("privacy.consent.recorded", r"(?i)\bconsent\s+(?:is\s+)?(?:recorded|captured|stored)\b"),
        ("frontend.csp.present", r"(?i)\bcontent[- ]security[- ]policy\s+(?:is\s+)?(?:present|configured|enabled)\b"),
        ("frontend.cookie.secure_httponly", r"(?i)\bcookies?\s+(?:are\s+)?(?:secure\s+and\s+)?httpOnly\b"),
        ("network.mesh.mtls_required", r"(?i)\bmTLS\s+(?:is\s+)?(?:required|enforced)\b"),
        ("network.egress.allowlist_enabled", r"(?i)\begress\s+allowlist\s+(?:is\s+)?(?:enabled|enforced)\b"),
        ("platform.tenant_isolation.enforced", r"(?i)\btenant\s+isolation\s+(?:is\s+)?(?:enforced|required)\b"),
        ("supply_chain.dependencies.pinned", r"(?i)\bdependencies\s+(?:are\s+)?pinned\b"),
    ]
    for predicate, pattern in bool_true:
        for match in re.finditer(pattern, text):
            add(predicate, True, match)

    bool_false = [
        ("security.encryption_at_rest.enabled", r"(?i)\bencryption\s+at\s+rest\s+(?:is\s+)?(?:disabled|off|not\s+enabled)\b"),
        ("api.rate_limit.enabled", r"(?i)\brate\s+limit(?:ing)?\s+(?:is\s+)?(?:disabled|off|not\s+enforced)\b"),
        ("kubernetes.readiness_probe.present", r"(?i)\bno\s+readiness\s+probe\b"),
        ("messaging.dlq.present", r"(?i)\bno\s+(?:dead[- ]letter\s+queue|DLQ)\b"),
    ]
    for predicate, pattern in bool_false:
        for match in re.finditer(pattern, text):
            add(predicate, False, match)

    for match in TLS_POLICY_RE.finditer(text):
        add("security.tls_policy.id", match.group(1).lower(), match)
    for match in LICENSE_RE.finditer(text):
        add("supply_chain.license.id", match.group(1), match)

    # Explicit sensitive logging claims in prose.
    for match in re.finditer(r"(?i)\b(?:logs?\s+may\s+include|log(?:ging)?\s+(?:includes?|contains?))\b.{0,40}\b(pan|ssn|password|credit\s*card)\b", text):
        add("privacy.sensitive_log.present", True, match)

    return hits


def extract_secrets(text: str, artifact: dict[str, Any], subjects: dict[str, str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for match in SECRET_LITERAL_RE.finditer(text):
        item = _candidate(
            predicate="security.secret_in_source.present",
            value=True,
            artifact=artifact,
            text=text,
            start=match.start(),
            end=match.end(),
            subjects=subjects,
            evidence_prefix="EXT-sec",
        )
        if item:
            hits.append(item)
    for match in SENSITIVE_LOG_RE.finditer(text):
        item = _candidate(
            predicate="privacy.sensitive_log.present",
            value=True,
            artifact=artifact,
            text=text,
            start=match.start(),
            end=match.end(),
            subjects=subjects,
            evidence_prefix="EXT-pii",
        )
        if item:
            hits.append(item)
    return hits


def extract_python(text: str, artifact: dict[str, Any], subjects: dict[str, str]) -> list[dict[str, Any]]:
    hits = extract_secrets(text, artifact, subjects)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return hits

    class Visitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                name = ""
                if isinstance(target, ast.Name):
                    name = target.id
                elif isinstance(target, ast.Attribute):
                    name = target.attr
                lname = name.lower()
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                    if any(token in lname for token in ("ttl", "session_lifetime", "max_age")):
                        item = _candidate(
                            predicate="session.ttl_seconds",
                            value=int(node.value.value),
                            artifact=artifact,
                            text=text,
                            start=node.lineno and 0 or 0,
                            end=0,
                            subjects=subjects,
                            evidence_prefix="EXT-py",
                        )
                        # Prefer byte offsets from source segment when available.
                        if item:
                            try:
                                segment = ast.get_source_segment(text, node) or name
                                start = text.find(segment)
                                if start >= 0:
                                    item["locator"] = _line_span(text, start, start + len(segment))
                                    item["evidence_id"] = f"EXT-py-session_ttl_seconds-{start}"
                            except Exception:
                                pass
                            hits.append(item)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if any(token in lname for token in ("api_key", "secret", "password", "token")) and len(node.value.value) >= 8:
                        item = _candidate(
                            predicate="security.secret_in_source.present",
                            value=True,
                            artifact=artifact,
                            text=text,
                            start=0,
                            end=0,
                            subjects=subjects,
                            evidence_prefix="EXT-py",
                        )
                        if item:
                            segment = ast.get_source_segment(text, node) or node.value.value
                            start = text.find(segment)
                            if start >= 0:
                                item["locator"] = _line_span(text, start, start + len(segment))
                                item["evidence_id"] = f"EXT-py-secret_in_source-{start}"
                            hits.append(item)
            self.generic_visit(node)

        def _emit(self, predicate: str, node: ast.AST) -> None:
            segment = ast.get_source_segment(text, node) or ""
            if not segment:
                return
            start = text.find(segment)
            if start < 0:
                return
            item = _candidate(
                predicate=predicate,
                value=True,
                artifact=artifact,
                text=text,
                start=start,
                end=start + len(segment),
                subjects=subjects,
                evidence_prefix="EXT-py",
            )
            if item:
                hits.append(item)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_fn(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_fn(node)

        def _visit_fn(self, node: ast.AST) -> None:
            name = getattr(node, "name", "").lower()
            if "auth" in name and "middleware" in name:
                self._emit("api.auth_middleware.present", node)
            for dec in getattr(node, "decorator_list", []):
                segment = (ast.get_source_segment(text, dec) or "").lower()
                if "middleware" in segment and ("auth" in name or "auth" in segment):
                    self._emit("api.auth_middleware.present", node)
                if "ratelimit" in segment or "rate_limit" in segment:
                    self._emit("api.rate_limit.enabled", node)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            lname = name.lower()
            segment = (ast.get_source_segment(text, node) or "").lower()
            if lname in {"middleware", "add_middleware"} or "auth" in lname:
                if "auth" in segment or "auth" in lname:
                    self._emit("api.auth_middleware.present", node)
            if "ratelimit" in lname or "rate_limit" in lname or "ratelimit" in segment:
                self._emit("api.rate_limit.enabled", node)
            self.generic_visit(node)

    Visitor().visit(tree)
    # Also apply markdown-style claims inside comments/docstrings lightly via full-text scan
    # for TTL phrases embedded in Python files.
    hits.extend([
        h for h in extract_markdown(text, artifact, subjects)
        if h["predicate"] in {
            "session.ttl_seconds", "session.idle_timeout_seconds",
            "security.encryption_at_rest.enabled", "security.tls_policy.id",
        }
    ])
    return hits


def extract_go(text: str, artifact: dict[str, Any], subjects: dict[str, str]) -> list[dict[str, Any]]:
    hits = extract_secrets(text, artifact, subjects)
    # time.Duration style: 12 * time.Minute, 600 * time.Second
    for match in re.finditer(
        r"(?i)(\d+)\s*\*\s*time\.(Second|Minute|Hour)",
        text,
    ):
        # Only bind to session TTL when nearby context mentions session/ttl/cookie.
        window_start = max(0, match.start() - 120)
        window = text[window_start:match.end() + 40]
        if re.search(r"(?i)session|ttl|maxage|cookie", window):
            seconds = _to_seconds(float(match.group(1)), match.group(2))
            item = _candidate(
                predicate="session.ttl_seconds",
                value=seconds,
                artifact=artifact,
                text=text,
                start=match.start(),
                end=match.end(),
                subjects=subjects,
                evidence_prefix="EXT-go",
            )
            if item:
                hits.append(item)
    # const SessionTTL = 720  (bare seconds only; duration form handled above)
    for match in re.finditer(
        r"(?i)(?:const|var)\s+\w*(?:Session|TTL|MaxAge)\w*\s*=\s*(\d+)\s*(?:;|//|/\*|$)",
        text,
        re.M,
    ):
        item = _candidate(
            predicate="session.ttl_seconds",
            value=int(match.group(1)),
            artifact=artifact,
            text=text,
            start=match.start(),
            end=match.end(),
            subjects=subjects,
            evidence_prefix="EXT-go",
        )
        if item:
            hits.append(item)
    if re.search(r"(?i)Use\([^)]*Auth|middleware\.Auth|RequireAuth|authMiddleware", text):
        match = re.search(r"(?i)Use\([^)]*Auth|middleware\.Auth|RequireAuth|authMiddleware", text)
        if match:
            item = _candidate(
                predicate="api.auth_middleware.present",
                value=True,
                artifact=artifact,
                text=text,
                start=match.start(),
                end=match.end(),
                subjects=subjects,
                evidence_prefix="EXT-go",
            )
            if item:
                hits.append(item)
    if re.search(r"(?i)RateLimit|httprate|tollbooth", text):
        match = re.search(r"(?i)RateLimit|httprate|tollbooth", text)
        if match:
            item = _candidate(
                predicate="api.rate_limit.enabled",
                value=True,
                artifact=artifact,
                text=text,
                start=match.start(),
                end=match.end(),
                subjects=subjects,
                evidence_prefix="EXT-go",
            )
            if item:
                hits.append(item)
    hits.extend([
        h for h in extract_markdown(text, artifact, subjects)
        if h["predicate"] in {
            "session.ttl_seconds", "session.idle_timeout_seconds",
            "security.encryption_at_rest.enabled", "security.tls_policy.id",
        }
    ])
    return hits


def extract_json_config(text: str, artifact: dict[str, Any], subjects: dict[str, str]) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    hits: list[dict[str, Any]] = []
    flat_keys = {
        "session.ttl_seconds": ("session_ttl_seconds", "ttl_seconds", "sessionTtlSeconds"),
        "security.encryption_at_rest.enabled": ("encryption_at_rest", "encryptionAtRest"),
        "security.tls_policy.id": ("tls_policy", "tlsPolicy"),
        "kubernetes.deployment.replicas": ("replicas",),
    }

    def walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(obj, (int, float, bool, str)):
            leaf = path.split(".")[-1]
            for predicate, aliases in flat_keys.items():
                if leaf in aliases or path.endswith(predicate):
                    # Find approximate location by key name in source.
                    key_name = leaf
                    match = re.search(rf'"{re.escape(key_name)}"\s*:', text)
                    if not match:
                        continue
                    item = _candidate(
                        predicate=predicate,
                        value=value if not isinstance(value, float) else int(value) if value == int(value) else value,
                        artifact=artifact,
                        text=text,
                        start=match.start(),
                        end=match.end(),
                        subjects=subjects,
                        evidence_prefix="EXT-json",
                    )
                    if item:
                        hits.append(item)

    walk(data)
    return hits


def _resolve_conflicts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in candidates:
        key = (item["predicate"], item["subject"])
        by_key.setdefault(key, []).append(item)
    out: list[dict[str, Any]] = []
    for key, group in sorted(by_key.items()):
        values = {json.dumps(item["value"], sort_keys=True) if isinstance(item["value"], (dict, list)) else item["value"] for item in group}
        if len(values) != 1:
            continue  # conflict → drop
        # Prefer first occurrence; dedupe evidence_ids
        chosen = group[0]
        out.append(chosen)
    # Ensure unique evidence_ids
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for index, item in enumerate(out):
        eid = item["evidence_id"]
        if eid in seen:
            item = dict(item)
            item["evidence_id"] = f"{eid}-{index}"
        seen.add(item["evidence_id"])
        unique.append(item)
    return unique


def extract_observations(package: dict[str, Any]) -> list[dict[str, Any]]:
    """Return extracted observations; empty list if nothing high-confidence matched."""
    subjects = _subjects()
    artifacts = _artifacts_from_package(package)
    candidates: list[dict[str, Any]] = []
    for artifact in artifacts:
        lang = artifact["language"]
        text = artifact["content"]
        if lang == "markdown":
            candidates.extend(extract_markdown(text, artifact, subjects))
            candidates.extend(extract_secrets(text, artifact, subjects))
        elif lang == "python":
            candidates.extend(extract_python(text, artifact, subjects))
        elif lang == "go":
            candidates.extend(extract_go(text, artifact, subjects))
        elif lang == "json":
            candidates.extend(extract_json_config(text, artifact, subjects))
            candidates.extend(extract_secrets(text, artifact, subjects))
        else:
            candidates.extend(extract_markdown(text, artifact, subjects))
            candidates.extend(extract_secrets(text, artifact, subjects))
    return _resolve_conflicts(candidates)


def ensure_observations(package: dict[str, Any]) -> dict[str, Any]:
    """Return a package copy with observations filled via extraction when omitted/empty."""
    out = dict(package)
    existing = out.get("observations")
    if isinstance(existing, list) and existing:
        return out
    extracted = extract_observations(out)
    out["observations"] = extracted
    out["extraction"] = {
        "extractor": EXTRACTOR_ID,
        "extractor_version": EXTRACTOR_VERSION,
        "observation_count": len(extracted),
    }
    return out
