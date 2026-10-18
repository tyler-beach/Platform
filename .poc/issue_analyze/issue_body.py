#!/usr/bin/env python3
"""Build Pathfinder analyze issue bodies for GitHub Issues intake.

Used by tests and kept in sync with the Pages demo helper. Does not evaluate.
"""
from __future__ import annotations

from typing import Any

ATTESTATION_LINE = (
    "I attest this submission contains only synthetic or explicitly public content "
    "and no secrets or confidential source."
)
MAX_URL_BODY_CHARS = 5500


def build_issue_body(
    *,
    tech_spec: str = "",
    code: str = "",
    domains: str = "",
    attested: bool = False,
) -> str:
    check = "[X]" if attested else "[ ]"
    domains_text = domains.strip()
    tech = tech_spec.strip()
    sample = code.strip()
    parts = [
        "### Public / synthetic attestation",
        "",
        f"- {check} {ATTESTATION_LINE}",
        "",
        "### Domains (optional scope filter)",
        "",
        domains_text if domains_text else "_Leave blank to evaluate all domains._",
        "",
        "### Tech spec (markdown)",
        "",
        tech if tech else "_No tech spec provided._",
        "",
        "### Sample code",
        "",
        sample if sample else "_No sample code provided._",
        "",
        "### Observations JSON array (optional)",
        "",
        "_Left empty so Actions can run paste extraction._",
        "",
    ]
    return "\n".join(parts)


def validate_prepare(*, tech_spec: str, code: str, attested: bool) -> str | None:
    if not attested:
        return "Public/synthetic attestation is required before opening GitHub."
    if not tech_spec.strip() and not code.strip():
        return "Provide a tech spec and/or sample code."
    return None


def github_new_issue_url(
    repository: str,
    *,
    title: str,
    body: str,
    labels: str = "pathfinder-analyze",
) -> dict[str, Any]:
    """Return open strategy: embed body in URL when short enough, else copy-only."""
    from urllib.parse import quote

    base = f"https://github.com/{repository}/issues/new"
    if len(body) <= MAX_URL_BODY_CHARS:
        query = (
            f"title={quote(title)}"
            f"&labels={quote(labels)}"
            f"&body={quote(body)}"
        )
        return {"mode": "url_body", "url": f"{base}?{query}", "copy_required": False}
    template = f"{base}?template=pathfinder-analyze.yml&title={quote(title)}"
    return {"mode": "copy_then_template", "url": template, "copy_required": True}
