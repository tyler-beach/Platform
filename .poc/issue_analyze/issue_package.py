#!/usr/bin/env python3
"""Parse a Pathfinder analyze GitHub issue into an evidence package and render results.

Public-repo safety: result comments include hashes/outcomes, not full source bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = ROOT / ".poc" / "requirement_engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import evaluate_package  # noqa: E402
import package_collector  # noqa: E402
import paste_extractor  # noqa: E402

MAX_FIELD_CHARS = 50_000
MAX_PACKAGE_CHARS = 200_000
PACKAGE_FENCE_RE = re.compile(
    r"```(?:pathfinder-package|json)\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
SECTION_RE = re.compile(
    r"###\s+(?P<title>.+?)\s*\n(?P<body>.*?)(?=\n###\s+|\Z)",
    re.DOTALL,
)


class IntakeError(ValueError):
    """Issue body cannot be turned into a safe evaluation package."""


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def parse_form_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in SECTION_RE.finditer(body or ""):
        sections[_normalize_title(match.group("title"))] = match.group("body").strip()
    return sections


def attestation_accepted(body: str, sections: dict[str, str]) -> bool:
    text = (body or "") + "\n" + "\n".join(sections.values())
    patterns = [
        r"\[x\].*synthetic or explicitly public",
        r"\[X\].*synthetic or explicitly public",
        r"attestation.*\n.*\[x\]",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def extract_package_json(body: str, sections: dict[str, str]) -> dict[str, Any] | None:
    # Prefer explicit form field.
    for key in ("full package json (preferred)", "full package json", "package json"):
        if key in sections and sections[key].strip():
            raw = sections[key].strip()
            fence = PACKAGE_FENCE_RE.search(raw)
            raw = fence.group(1).strip() if fence else raw
            if len(raw) > MAX_PACKAGE_CHARS:
                raise IntakeError(f"package JSON exceeds {MAX_PACKAGE_CHARS} characters")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise IntakeError(f"full package JSON is invalid: {exc}") from exc
            if not isinstance(value, dict):
                raise IntakeError("full package JSON must be an object")
            return value
    fence = PACKAGE_FENCE_RE.search(body or "")
    if fence:
        raw = fence.group(1).strip()
        if len(raw) > MAX_PACKAGE_CHARS:
            raise IntakeError(f"package JSON exceeds {MAX_PACKAGE_CHARS} characters")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IntakeError(f"fenced package JSON is invalid: {exc}") from exc
        if not isinstance(value, dict):
            raise IntakeError("fenced package JSON must be an object")
        return value
    return None


def _parse_domains(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]


def _bounded(label: str, value: str) -> str:
    if len(value) > MAX_FIELD_CHARS:
        raise IntakeError(f"{label} exceeds {MAX_FIELD_CHARS} characters")
    return value


def _guess_code_path(code: str) -> str:
    if "package main" in code or re.search(r"\bfunc\s+\w+\s*\(", code):
        return "issue/sample.go"
    if re.search(r"^\s*(def|class|import|from)\s+", code, re.M) or "async def" in code:
        return "issue/sample.py"
    if re.search(r"(?m)^(apiVersion|kind):\s*\S+", code):
        return "issue/manifest.yaml"
    if code.lstrip().startswith("{"):
        return "issue/config.json"
    return "issue/sample-code.txt"


def build_package_from_fields(sections: dict[str, str], *, issue_number: int) -> dict[str, Any]:
    tech = _bounded("tech spec", sections.get("tech spec (markdown)", sections.get("tech spec", "")))
    code = _bounded("sample code", sections.get("sample code", sections.get("code", "")))
    obs_raw = sections.get("observations json array", sections.get("observations json", sections.get("observations", "")))
    domains = _parse_domains(sections.get("domains (optional scope filter)", sections.get("domains", "")))
    if not tech.strip() and not code.strip() and not obs_raw.strip():
        raise IntakeError("provide tech spec and/or sample code (or full package JSON / observations)")

    observations: list[Any] = []
    if obs_raw.strip():
        try:
            observations = json.loads(obs_raw)
        except json.JSONDecodeError as exc:
            raise IntakeError(f"observations JSON is invalid: {exc}") from exc
        if not isinstance(observations, list):
            raise IntakeError("observations must be a JSON array")

    package: dict[str, Any] = {
        "schema_version": "pathfinder-evidence-package-v1",
        "package_id": f"github-issue-{issue_number}",
        "scope": {"domains": domains} if domains else {},
        "observations": [],
    }
    tech_sha = _sha(tech) if tech else None
    if tech:
        package["tech_spec"] = {
            "artifact_id": "tech_spec",
            "path": "issue/tech-spec.md",
            "revision": f"sha256:{tech_sha}",
            "sha256": tech_sha,
            "content": tech,
        }
    if code:
        code_sha = _sha(code)
        code_path = _guess_code_path(code)
        package["code"] = [{
            "artifact_id": "code-0",
            "path": code_path,
            "revision": f"sha256:{code_sha}",
            "sha256": code_sha,
            "content": code,
        }]

    for index, item in enumerate(observations):
        if not isinstance(item, dict):
            raise IntakeError(f"observations[{index}] must be an object")
        obs = dict(item)
        if "artifact_id" not in obs:
            obs["artifact_id"] = "tech_spec" if tech else "code-0"
        if "path" not in obs:
            if obs["artifact_id"] == "tech_spec":
                obs["path"] = "issue/tech-spec.md"
            else:
                obs["path"] = package.get("code", [{"path": "issue/sample-code.txt"}])[0]["path"]
        if "revision" not in obs or "source_sha256" not in obs:
            if obs["artifact_id"] == "tech_spec" and tech_sha:
                obs["revision"] = f"sha256:{tech_sha}"
                obs["source_sha256"] = tech_sha
            elif package.get("code"):
                obs["revision"] = package["code"][0]["revision"]
                obs["source_sha256"] = package["code"][0]["sha256"]
            else:
                raise IntakeError(
                    f"observations[{index}] needs source_sha256/revision when no tech_spec/code content is supplied"
                )
        if "locator" not in obs:
            obs["locator"] = {"kind": "issue_claim", "value": obs.get("predicate", f"obs-{index}")}
        package["observations"].append(obs)
    return package


def _pin_artifact_hashes(package: dict[str, Any]) -> dict[str, Any]:
    """Recompute content digests so issue paste stubs cannot drift from body text."""
    out = dict(package)
    artifact_digests: dict[str, str] = {}
    tech = out.get("tech_spec")
    if isinstance(tech, dict) and isinstance(tech.get("content"), str) and tech["content"].strip():
        tech = dict(tech)
        digest = _sha(tech["content"])
        tech["sha256"] = digest
        tech["revision"] = f"sha256:{digest}"
        tech.setdefault("artifact_id", "tech_spec")
        tech.setdefault("path", "issue/tech-spec.md")
        out["tech_spec"] = tech
        artifact_digests[tech["artifact_id"]] = digest
    code_blocks = []
    for index, block in enumerate(out.get("code") or []):
        if not isinstance(block, dict) or not isinstance(block.get("content"), str):
            code_blocks.append(block)
            continue
        item = dict(block)
        digest = _sha(item["content"])
        item["sha256"] = digest
        item["revision"] = f"sha256:{digest}"
        item.setdefault("artifact_id", f"code-{index}")
        item.setdefault("path", f"issue/sample-code-{index}.txt")
        code_blocks.append(item)
        artifact_digests[item["artifact_id"]] = digest
    if code_blocks:
        out["code"] = code_blocks
    observations = []
    for item in out.get("observations") or []:
        if not isinstance(item, dict):
            observations.append(item)
            continue
        obs = dict(item)
        artifact_id = obs.get("artifact_id")
        if artifact_id in artifact_digests:
            digest = artifact_digests[artifact_id]
            obs["source_sha256"] = digest
            obs["revision"] = f"sha256:{digest}"
        observations.append(obs)
    if "observations" in out:
        out["observations"] = observations
    return out


def package_from_issue(body: str, *, issue_number: int) -> dict[str, Any]:
    sections = parse_form_sections(body)
    if not attestation_accepted(body, sections):
        raise IntakeError("public/synthetic attestation checkbox is required")
    package = extract_package_json(body, sections)
    if package is None:
        package = build_package_from_fields(sections, issue_number=issue_number)
    package = dict(package)
    package.setdefault("package_id", f"github-issue-{issue_number}")
    if package.get("schema_version") != "pathfinder-evidence-package-v1":
        raise IntakeError("package schema_version must be pathfinder-evidence-package-v1")
    package = _pin_artifact_hashes(package)
    # When observations are omitted, extract from pasted tech-spec/code (fail-closed).
    package = paste_extractor.ensure_observations(package)
    # Validate collectability early.
    package_collector.collect_package_observations(package)
    return package


def render_result_comment(report: dict[str, Any], *, run_url: str, package: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "## Pathfinder catalog evaluation",
        "",
        f"- **Aggregate status:** `{report['aggregate_status']}`",
        f"- **Meaning:** {report['aggregate_meaning']}",
        f"- **Catalog size:** {report['catalog_size']}",
        f"- **Observations used:** {report['observation_count']}",
        f"- **Package id:** `{package.get('package_id', 'unnamed')}`",
        f"- **Report fingerprint:** `{report['report_sha256']}`",
        f"- **Workflow run:** {run_url}",
    ]
    extraction = report.get("extraction") or package.get("extraction")
    if extraction:
        lines.append(
            f"- **Paste extractor:** `{extraction.get('extractor')}` "
            f"({extraction.get('observation_count', 0)} observations)"
        )
    lines.extend([
        "",
        "### Outcome counts",
        "",
        f"| Outcome | Count |",
        f"|---|---:|",
        f"| supported_deviation | {counts['supported_deviation']} |",
        f"| no_deviation_found | {counts['no_deviation_found']} |",
        f"| inconclusive | {counts['inconclusive']} |",
        f"| not_applicable | {counts['not_applicable']} |",
        "",
        "### Notable requirements",
        "",
    ])
    notable = [
        row for row in report["results"]
        if row["outcome"] in {"supported_deviation", "no_deviation_found"}
    ][:20]
    if not notable:
        lines.append("_No confident aligned/deviation results; most in-scope requirements were inconclusive or out of scope._")
    else:
        lines.append("| ADR | Domain | Outcome | Predicate |")
        lines.append("|---|---|---|---|")
        for row in notable:
            lines.append(
                f"| `{row['adr_id']}` | {row.get('domain', '')} | `{row['outcome']}` | `{row['predicate']}` |"
            )
    lines.extend([
        "",
        "### Evidence boundary",
        "",
        "- Full tech-spec/code bodies are **not** copied into this comment.",
        "- Download the workflow artifact `pathfinder-issue-evaluation` for the full report JSON.",
        "- Catalog labels remain `synthetic_unadjudicated`. Missing observations stay `inconclusive`.",
        "- This comment does not waive ADRs, mutate production, or create training labels.",
    ])
    # Ensure we never accidentally include package source content.
    comment = "\n".join(lines) + "\n"
    for block in filter(None, [
        (package.get("tech_spec") or {}).get("content"),
        *((item.get("content") for item in package.get("code") or [])),
    ]):
        if isinstance(block, str) and len(block) > 40 and block in comment:
            raise IntakeError("refusing to post a comment that embeds source content")
    return comment


def render_error_comment(message: str, *, run_url: str) -> str:
    return (
        "## Pathfinder catalog evaluation failed\n\n"
        f"{message}\n\n"
        f"Workflow run: {run_url}\n\n"
        "Fix the issue body (attestation, package schema, or paste content) and edit the issue to re-run.\n"
        "See `docs/ISSUE_ANALYZE_WORKFLOW.md`.\n"
    )


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--run-url", default=os.environ.get("RUN_URL", ""))
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--comment", action="store_true", help="Post result/error comment via gh")
    parser.add_argument("--body-file", type=Path, help="Use local issue body instead of gh api")
    args = parser.parse_args(argv)
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="pathfinder-issue-"))
    work.mkdir(parents=True, exist_ok=True)
    run_url = args.run_url or "(local run)"

    try:
        if args.body_file:
            body = args.body_file.read_text(encoding="utf-8")
            title = "[Pathfinder analyze] local"
        else:
            if not args.repo:
                raise IntakeError("GITHUB_REPOSITORY / --repo is required")
            issue = _gh_json(["api", f"repos/{args.repo}/issues/{args.issue_number}"])
            body = issue.get("body") or ""
            title = issue.get("title") or ""
        if "[pathfinder analyze]" not in title.lower() and "pathfinder-analyze" not in body.lower():
            # Still allow labeled issues with form bodies.
            if "public / synthetic attestation" not in body.lower():
                raise IntakeError("issue is not a Pathfinder analyze submission")

        package = package_from_issue(body, issue_number=args.issue_number)
        package_path = work / "package.json"
        package_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = evaluate_package.evaluate_package(package)
        report_path = work / "report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        comment = render_result_comment(report, run_url=run_url, package=package)
        (work / "comment.md").write_text(comment, encoding="utf-8")
        print(json.dumps({
            "ok": True,
            "aggregate_status": report["aggregate_status"],
            "counts": report["counts"],
            "package_path": str(package_path),
            "report_path": str(report_path),
        }))
    except (IntakeError, ValueError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        message = str(exc)
        comment = render_error_comment(message, run_url=run_url)
        (work / "comment.md").write_text(comment, encoding="utf-8")
        print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
        if args.comment:
            if not args.repo:
                raise SystemExit("repo required to comment")
            subprocess.run(
                ["gh", "issue", "comment", str(args.issue_number), "--repo", args.repo, "--body-file", str(work / "comment.md")],
                check=True,
            )
        return 2

    if args.comment:
        if not args.repo:
            raise SystemExit("repo required to comment")
        subprocess.run(
            ["gh", "issue", "comment", str(args.issue_number), "--repo", args.repo, "--body-file", str(work / "comment.md")],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
