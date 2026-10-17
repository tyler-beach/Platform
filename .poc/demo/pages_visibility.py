"""Fail-closed guard for publishing run details to a GitHub Pages artifact."""
from __future__ import annotations


def real_data_export_enabled(repository_visibility: str, pages_public: bool | None, opt_in: str) -> bool:
    """Return false when disabled; require private repo + non-public Pages when enabled."""
    if opt_in != "true":
        return False
    if repository_visibility != "private":
        raise ValueError("real Pages data requires repository visibility=private")
    if pages_public is not False:
        raise ValueError("real Pages data requires the Pages API to confirm public=false")
    return True
