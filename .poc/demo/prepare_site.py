#!/usr/bin/env python3
"""Set no-JavaScript workflow links to this checked-out repository."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_REPOSITORY = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}\Z")
_LINKS = {
    "demo-open-analysis": "poc-analysis.yml",
    "demo-open-evaluation": "poc-evaluation.yml",
    "demo-guide-analysis": "poc-analysis.yml",
    "demo-guide-evaluation": "poc-evaluation.yml",
}


def prepare_site(site_dir: str | Path, repository: str) -> None:
    if not _REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use a valid owner/name form")
    page = Path(site_dir) / "demo" / "index.html"
    html = page.read_text(encoding="utf-8")
    for element_id, workflow in _LINKS.items():
        pattern = re.compile(rf'(<a\b(?=[^>]*\bid="{element_id}")[^>]*\bhref=")[^"]*(")')
        url = f"https://github.com/{repository}/actions/workflows/{workflow}"
        html, count = pattern.subn(lambda match: match.group(1) + url + match.group(2), html, count=1)
        if count != 1:
            raise ValueError(f"expected one generated workflow link with id={element_id}")
    page.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", default="site")
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    prepare_site(args.site_dir, args.repository)
    print(f"Prepared demo workflow links for {args.repository}.")


if __name__ == "__main__":
    main()
