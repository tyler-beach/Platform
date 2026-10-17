"""Fail-closed guard for publishing run details to a GitHub Pages artifact."""
from __future__ import annotations


def real_data_export_enabled(repository_visibility: str, repository_owner_type: str,
                             pages_public: bool | None, opt_in: str) -> bool:
    """Return false when disabled; otherwise require an organization repo and private Pages."""
    if opt_in != "true":
        return False
    if repository_owner_type != "Organization":
        raise ValueError("real Pages data requires an organization-owned repository")
    if repository_visibility not in {"private", "internal"}:
        raise ValueError("real Pages data requires repository visibility=private or internal")
    if pages_public is not False:
        raise ValueError("real Pages data requires the Pages API to confirm public=false")
    return True
