"""Parse Pathfinder-oriented ADR markdown structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Supports both "- **Domain:** identity" and "- **Domain**: identity"
META_RE = re.compile(
    r"^\s*[-*]\s*\*\*(?P<key>[^*:]+?)(?::\*\*|\*\*\s*:)\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
SECTION_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")
ADR_ID_RE = re.compile(r"\b(ADR[-_][A-Z0-9][-A-Z0-9]*)\b", re.IGNORECASE)


@dataclass
class ParsedADR:
    path: Path
    title: str = ""
    adr_id: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def decision(self) -> str:
        for key in ("decision", "decisions"):
            if key in self.sections and self.sections[key].strip():
                return self.sections[key].strip()
        return ""

    @property
    def domain(self) -> str:
        for key in ("domain", "domains"):
            if key in self.meta:
                # take first token / first list item
                raw = self.meta[key]
                return raw.split(",")[0].split()[0].strip().lower()
        return ""

    @property
    def status(self) -> str:
        return self.meta.get("status", "").strip()


def parse_adr_markdown(path: Path) -> ParsedADR:
    text = path.read_text(encoding="utf-8")
    parsed = ParsedADR(path=path)
    lines = text.splitlines()
    if not lines:
        parsed.errors.append("file is empty")
        return parsed

    for line in lines[:5]:
        m = HEADING_RE.match(line)
        if m:
            parsed.title = m.group("title").strip()
            break
    if not parsed.title:
        parsed.errors.append("missing top-level # title")

    id_match = ADR_ID_RE.search(parsed.title) or ADR_ID_RE.search(path.name)
    if id_match:
        parsed.adr_id = id_match.group(1).upper().replace("_", "-")
    else:
        parsed.warnings.append("could not detect ADR id from title or filename")

    # metadata bullets before first ##
    body_start = 0
    for i, line in enumerate(lines):
        if SECTION_RE.match(line):
            body_start = i
            break
        m = META_RE.match(line)
        if m:
            key = m.group("key").strip().lower()
            parsed.meta[key] = m.group("value").strip()
    else:
        body_start = len(lines)

    current = None
    buf: list[str] = []
    for line in lines[body_start:]:
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

    if not parsed.decision:
        parsed.errors.append("missing ## Decision section with content")
    if not parsed.domain:
        parsed.warnings.append("missing Domain metadata")
    if not parsed.status:
        parsed.warnings.append("missing Status metadata")

    # strip parenthetical noise from title after em dash
    if "—" in parsed.title:
        parsed.title = parsed.title.split("—", 1)[-1].strip()
    elif " - " in parsed.title and parsed.adr_id:
        parsed.title = parsed.title.split(" - ", 1)[-1].strip()

    return parsed


def list_adr_files(adrs_dir: Path) -> list[Path]:
    return sorted(p for p in adrs_dir.glob("*.md") if p.is_file())
