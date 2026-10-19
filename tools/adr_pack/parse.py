"""Parse Pathfinder-oriented ADR markdown, including MADR format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Supports:
# - "- **Domain:** identity" (colon inside bold)
# - "- **Domain**: identity" (colon outside bold)
# - MADR-style "* Status: accepted"
META_PATTERNS = (
    re.compile(
        r"^\s*[-*]\s*\*\*(?P<key>[^*:]+):\*\*\s*(?P<value>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*[-*]\s*\*\*(?P<key>[^*]+)\*\*\s*:\s*(?P<value>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*[-*]\s*(?P<key>[A-Za-z][A-Za-z0-9 _/-]*?)\s*:\s*(?P<value>.+?)\s*$",
        re.IGNORECASE,
    ),
)
HEADING_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
SECTION_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")
ADR_ID_RE = re.compile(r"\b(ADR[-_][A-Z0-9][-A-Z0-9]*)\b", re.IGNORECASE)
MADR_NUM_RE = re.compile(r"^(\d{4})(?:-|\.)")
FRONTMATTER_BOUNDARY = re.compile(r"^---\s*$")

# Prefer MADR's Decision Outcome, then Pathfinder ## Decision.
DECISION_SECTION_KEYS = (
    "decision outcome",
    "decision",
    "decisions",
)

SKIP_NAMES = {
    "readme.md",
    "adr-template.md",
    "index.md",
    "template.md",
}


@dataclass
class ParsedADR:
    path: Path
    title: str = ""
    adr_id: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    format_hint: str = ""

    @property
    def decision(self) -> str:
        for key in DECISION_SECTION_KEYS:
            if key in self.sections and self.sections[key].strip():
                return self.sections[key].strip()
        return ""

    @property
    def domain(self) -> str:
        for key in ("domain", "domains", "category", "categories"):
            if key not in self.meta:
                continue
            raw = self.meta[key].strip()
            # YAML-ish list: [a, b] or a, b
            raw = raw.strip("[]")
            first = raw.split(",")[0].strip().strip("'\"")
            if first:
                return first.split()[0].strip().lower()
        return ""

    @property
    def status(self) -> str:
        return self.meta.get("status", "").strip()


def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Return (meta, index_after_frontmatter). index is 0 if none."""
    if not lines or not FRONTMATTER_BOUNDARY.match(lines[0]):
        return {}, 0
    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        if FRONTMATTER_BOUNDARY.match(lines[i]):
            return meta, i + 1
        line = lines[i].strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().strip("'\"")
        if key and value:
            meta[key] = value
    return {}, 0


def _detect_adr_id(title: str, path: Path) -> str:
    id_match = ADR_ID_RE.search(title) or ADR_ID_RE.search(path.name)
    if id_match:
        return id_match.group(1).upper().replace("_", "-")
    num = MADR_NUM_RE.match(path.name)
    if num:
        return f"ADR-{num.group(1)}"
    return ""


def parse_adr_markdown(path: Path) -> ParsedADR:
    text = path.read_text(encoding="utf-8")
    parsed = ParsedADR(path=path)
    lines = text.splitlines()
    if not lines:
        parsed.errors.append("file is empty")
        return parsed

    fm, body_offset = _parse_frontmatter(lines)
    parsed.meta.update(fm)
    if fm:
        parsed.format_hint = "madr"

    body_lines = lines[body_offset:]

    for line in body_lines[:12]:
        m = HEADING_RE.match(line)
        if m:
            parsed.title = m.group("title").strip()
            break
    if not parsed.title:
        parsed.errors.append("missing top-level # title")

    parsed.adr_id = _detect_adr_id(parsed.title, path)
    if not parsed.adr_id:
        parsed.warnings.append("could not detect ADR id from title or filename (expected ADR-… or NNNN-title.md)")

    # metadata bullets before first ## (MADR sometimes puts Status as list items)
    section_start = 0
    for i, line in enumerate(body_lines):
        if SECTION_RE.match(line):
            section_start = i
            break
        for pattern in META_PATTERNS:
            m = pattern.match(line)
            if not m:
                continue
            key = m.group("key").strip().lower()
            if key in {"deciders", "decision-makers", "decision makers"}:
                key = "decision-makers"
            parsed.meta[key] = m.group("value").strip()
            break
    else:
        section_start = len(body_lines)

    current = None
    buf: list[str] = []
    for line in body_lines[section_start:]:
        m = SECTION_RE.match(line)
        if m:
            if current is not None:
                parsed.sections[current] = "\n".join(buf).strip()
            current = m.group("name").strip().lower()
            buf = []
            continue
        if current is not None:
            buf.append(line)
    if current is not None:
        parsed.sections[current] = "\n".join(buf).strip()

    if "decision outcome" in parsed.sections:
        parsed.format_hint = parsed.format_hint or "madr"

    if not parsed.decision:
        parsed.errors.append(
            "missing ## Decision Outcome or ## Decision section with content"
        )
    if not parsed.domain:
        # MADR often has no Domain; parent folder can hint for categorized trees.
        parent = path.parent.name.lower()
        if parent not in {"", ".", "adrs", "decisions", "docs", "adr"}:
            parsed.meta.setdefault("category", parent)
            parsed.warnings.append(
                f"missing Domain/category metadata; using parent folder {parent!r} as category hint"
            )
        else:
            parsed.warnings.append(
                "missing Domain/category metadata (add YAML `categories:` or Domain bullet for Pathfinder applicability)"
            )
    if not parsed.status:
        parsed.warnings.append("missing Status metadata (YAML `status:` or Status bullet)")

    # strip parenthetical noise from title after em dash
    if "—" in parsed.title:
        parsed.title = parsed.title.split("—", 1)[-1].strip()
    elif " - " in parsed.title and parsed.adr_id:
        parsed.title = parsed.title.split(" - ", 1)[-1].strip()

    return parsed


def list_adr_files(adrs_dir: Path) -> list[Path]:
    """Collect ADR markdown files, including MADR category subfolders."""
    found = []
    for p in sorted(adrs_dir.rglob("*.md")):
        if not p.is_file():
            continue
        if p.name.lower() in SKIP_NAMES:
            continue
        found.append(p)
    return found
