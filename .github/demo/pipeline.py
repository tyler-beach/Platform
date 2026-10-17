#!/usr/bin/env python3
"""Deterministic, synthetic harness for the Functional Analysis Demo workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIXTURES = Path(".github/demo/fixtures")
EXPECTED = {
    "deviation": "supported_deviation",
    "aligned": "no_deviation_found",
    "insufficient-evidence": "inconclusive",
}
CASE_DIR = {"deviation": "deviation", "aligned": "aligned", "insufficient-evidence": "insufficient-evidence"}
DEMO_MAX_INPUT_TOKENS = 8000
DEMO_MAX_OUTPUT_TOKENS = 600
DEMO_MAX_CALLS = 1


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_summary(title: str, lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    body = "## " + title + "\n\n" + "\n".join(lines) + "\n\n"
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(body)
    print(body)


def copy_input(source: Path, target: Path, artifact_id: str, role: str, original: str, artifacts: list[dict[str, Any]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    value = digest(target)
    artifacts.append({
        "artifact_id": artifact_id,
        "role": role,
        "path": target.as_posix(),
        "original_fixture_path": original,
        "sha256": value,
        "version": "sha256:" + value,
        "byte_length": target.stat().st_size,
    })


def prepare(args: argparse.Namespace) -> None:
    root = Path(args.output)
    if root.exists():
        shutil.rmtree(root)
    (root / "input").mkdir(parents=True)
    scenario, sample = args.comparison, args.sample_case
    if scenario not in {"code-diff", "technical-spec", "spec-vs-implementation"}:
        raise ValueError("Unsupported comparison mode.")
    if sample not in EXPECTED:
        raise ValueError("Unsupported sample case.")

    selected_case = CASE_DIR[sample]
    artifacts: list[dict[str, Any]] = []
    adr_src = FIXTURES / "adr/ADR-001.md"
    copy_input(adr_src, root / "input/adr.md", "ART-ADR-001", "adr", adr_src.as_posix(), artifacts)

    if scenario in {"code-diff", "spec-vs-implementation"}:
        code_case = selected_case
        code_dir = FIXTURES / "code-diff" / code_case
        code_src = code_dir / "handler.go"
        diff_src = code_dir / "change.diff"
        copy_input(code_src, root / "input/handler.go", "ART-CODE-001", "implementation", code_src.as_posix(), artifacts)
        copy_input(diff_src, root / "input/change.diff", "ART-DIFF-001", "diff", diff_src.as_posix(), artifacts)

    if scenario == "technical-spec":
        spec_src = FIXTURES / "technical-spec" / (selected_case + ".md")
    elif scenario == "spec-vs-implementation":
        # The design requires asynchronous work; the selected code fixture varies.
        spec_src = FIXTURES / "technical-spec/aligned.md"
    else:
        spec_src = None

    if spec_src:
        copy_input(spec_src, root / "input/technical-spec.md", "ART-SPEC-001", "technical_spec", spec_src.as_posix(), artifacts)

    manifest = {
        "manifest_version": "1.0.0",
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "comparison": scenario,
        "sample_case": sample,
        "comparison_contract": {
            "code-diff": "implementation_vs_adr",
            "technical-spec": "technical_spec_vs_adr",
            "spec-vs-implementation": "technical_spec_vs_implementation",
        }[scenario],
        "artifacts": artifacts,
        "immutability_rule": "Each source version is the SHA-256 of the exact input bytes copied into this run bundle.",
    }
    save_json(root / "input-manifest.json", manifest)
    oracle = {
        "test_oracle_version": "1.0.0",
        "expected_outcome": EXPECTED[sample],
        "note": "Test oracle is used only by the final validator; it is not passed into the mock-model prompt context.",
    }
    save_json(root / "test-oracle.json", oracle)
    write_summary("1 · Admit and pin inputs", [
        f"- **Comparison:** `{scenario}`",
        f"- **Sample case:** `{sample}`",
        f"- **Source artifacts pinned:** {len(artifacts)}",
        "- Each input has a SHA-256 version recorded in `input-manifest.json`.",
        "- The oracle is kept separate from the evidence package and is not read by the mock-model stage.",
    ])


def classify_requirement(text: str) -> str:
    lower = text.lower()
    if re.search(r"\b(synchronously|synchronous|inline|before responding|before returning)\b", lower):
        return "synchronous"
    if re.search(r"\b(asynchronously|asynchronous|async|enqueue|queue|workflow|worker)\b", lower):
        return "asynchronous"
    return "unspecified"


def parse_requirements(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[dict[str, Any]] = []
    pending_heading = False
    for number, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text:
            pending_heading = False
            continue
        if re.match(r"^#{1,4}\s+Requirement\b", text, re.IGNORECASE):
            pending_heading = True
            continue
        has_normative = bool(re.search(r"\b(MUST|MUST NOT|SHALL|SHOULD|MAY)\b", text, re.IGNORECASE))
        if has_normative or (pending_heading and not text.startswith("#")):
            clean = re.sub(r"^[-*]\s*", "", text)
            result.append({
                "requirement_id": f"SPEC-R-{len(result)+1:03d}",
                "line": number,
                "text": clean,
                "classification": classify_requirement(clean),
            })
            pending_heading = False
    return result


def analyze(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    input_dir = root / "input"
    artifacts = {item["role"]: item for item in manifest["artifacts"]}
    adr_path = input_dir / "adr.md"
    adr_lines = adr_path.read_text(encoding="utf-8").splitlines()
    adr_constraints = [
        {"line": n, "text": line.strip()}
        for n, line in enumerate(adr_lines, 1)
        if re.search(r"\b(MUST|MUST NOT|SHALL|SHOULD)\b", line, re.IGNORECASE)
    ]
    requirements = parse_requirements(input_dir / "technical-spec.md") if (input_dir / "technical-spec.md").exists() else []
    ast = load_json(root / "ast-analysis.json") if (root / "ast-analysis.json").exists() else {
        "scanner": "not-applicable",
        "parse_status": "not_applicable",
        "source_sha256": None,
        "observations": [],
        "scope_note": "No implementation file is part of the selected comparison; the deterministic document pass is used.",
    }
    if "implementation" in artifacts and ast.get("parse_status") != "parsed":
        raise ValueError("Implementation input exists but the Go AST scanner did not produce a parsed result.")
    if "implementation" in artifacts and ast.get("source_sha256") != artifacts["implementation"]["sha256"]:
        raise ValueError("Go AST scanner hash does not match the pinned implementation bytes.")

    diff = input_dir / "change.diff"
    diff_added = []
    if diff.exists():
        diff_added = [line[1:].strip() for line in diff.read_text(encoding="utf-8").splitlines()
                      if line.startswith("+") and not line.startswith("+++")]

    result = {
        "analysis_version": "1.0.0",
        "comparison": manifest["comparison"],
        "comparison_contract": manifest["comparison_contract"],
        "static_analysis": ast,
        "adr_constraints": adr_constraints,
        "requirements": requirements,
        "diff_added_lines": diff_added,
        "analysis_notes": [
            "AST findings are observations of parsed call sites, not complete call-graph or runtime proofs.",
            "Markdown requirement extraction is deterministic and rule-based; ambiguity remains a valid result.",
            "No external model has been called.",
        ],
    }
    save_json(root / "analysis.json", result)
    observation_text = [f"- Line {o['line']}: `{o['call']}` → `{o['classification']}`"
                        for o in ast.get("observations", [])]
    if not observation_text:
        observation_text = ["- AST stage not applicable for this input; Markdown requirement extraction ran instead."]
    req_text = [f"- Line {r['line']}: `{r['classification']}` — {r['text']}" for r in requirements]
    if not req_text:
        req_text = ["- No technical-spec requirements were included in this comparison."]
    write_summary("2 · Deterministic parsing and analysis", [
        f"- **Comparison contract:** `{manifest['comparison_contract']}`",
        f"- **ADR constraints extracted:** {len(adr_constraints)}",
        f"- **Specification requirements extracted:** {len(requirements)}",
        *observation_text,
        *req_text,
        "- Scope note: the parser flags evidence for later review; it does not claim complete semantic analysis.",
    ])


def evidence(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    analysis = load_json(root / "analysis.json")
    artifact_by_role = {item["role"]: item for item in manifest["artifacts"]}
    items: list[dict[str, Any]] = []

    def add(eid: str, role: str, line_start: int, line_end: int, locator_kind: str,
            evidence_type: str, fact: str, excerpt: str) -> None:
        artifact = artifact_by_role[role]
        items.append({
            "evidence_id": eid,
            "artifact_id": artifact["artifact_id"],
            "artifact_version": artifact["version"],
            "source_path": artifact["path"],
            "locator": {"kind": locator_kind, "line_start": line_start, "line_end": line_end},
            "evidence_type": evidence_type,
            "fact": fact,
            "excerpt": excerpt,
        })

    for idx, item in enumerate(analysis["adr_constraints"]):
        # Keep the governing constraint and the asynchronous workflow rule available.
        add(f"EV-ADR-{idx+1:03d}", "adr", item["line"], item["line"], "source-line",
            "architectural_constraint", "Accepted ADR constraint", item["text"])

    if "implementation" in artifact_by_role:
        ast = analysis["static_analysis"]
        for idx, item in enumerate(ast.get("observations", [])):
            add(f"EV-AST-{idx+1:03d}", "implementation", item["line"], item["line"], "source-line",
                "ast_call_site", item["classification"] + ": " + item["reason"], item["call"])
        if "diff" in artifact_by_role:
            diff_lines = (root / artifact_by_role["diff"]["path"]).read_text(encoding="utf-8").splitlines()
            added = [(n, line[1:].strip()) for n, line in enumerate(diff_lines, 1)
                     if line.startswith("+") and not line.startswith("+++")]
            if added:
                joined = " | ".join(text for _, text in added[:4])
                add("EV-DIFF-001", "diff", added[0][0], added[min(3, len(added)-1)][0], "diff-line",
                    "change_diff", "Selected changed lines", joined)

    if "technical_spec" in artifact_by_role:
        for idx, item in enumerate(analysis["requirements"]):
            add(f"EV-SPEC-{idx+1:03d}", "technical_spec", item["line"], item["line"], "source-line",
                "technical_requirement", item["classification"] + ": " + item["text"], item["text"])

    package = {
        "evidence_contract_version": "1.0.0",
        "job_id": f"demo-{manifest['run_id']}",
        "comparison": manifest["comparison"],
        "comparison_contract": manifest["comparison_contract"],
        "source_artifacts": manifest["artifacts"],
        "completeness": {
            "adr_constraints_present": bool(analysis["adr_constraints"]),
            "implementation_ast_parsed": analysis["static_analysis"].get("parse_status") == "parsed",
            "specification_requirements_present": bool(analysis["requirements"]),
            "diff_present": "diff" in artifact_by_role,
        },
        "items": items,
    }
    if not items:
        raise ValueError("Evidence package is empty.")
    ids = [item["evidence_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Evidence IDs are not unique.")
    save_json(root / "evidence-package.json", package)
    save_json(root / "evidence-contract-check.json", {
        "contract_version": package["evidence_contract_version"],
        "item_count": len(items),
        "unique_ids": len(set(ids)),
        "missing_source_artifacts": [],
        "source_versions_are_pinned": all(bool(item.get("artifact_version", "").startswith("sha256:")) for item in items),
        "status": "valid",
    })
    preview = [f"- `{i['evidence_id']}` · `{i['evidence_type']}` · {i['source_path']}:{i['locator']['line_start']}"
               for i in items]
    write_summary("3 · Evidence contract", [
        f"- **Evidence schema:** `{package['evidence_contract_version']}`",
        f"- **Evidence items:** {len(items)}",
        f"- **Unique IDs:** {len(set(ids))}",
        "- Each item binds an evidence ID to an artifact ID, SHA-256 version, locator, type, excerpt and fact.",
        *preview,
    ])


def budget(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    package = load_json(root / "evidence-package.json")
    analysis = load_json(root / "analysis.json")
    request_context = json.dumps({
        "comparison": package["comparison"],
        "evidence": package["items"],
        "analysis": {
            "requirements": analysis["requirements"],
            "observations": analysis["static_analysis"].get("observations", []),
        },
        "prompt_version": "demo-assessment-v1",
        "output_schema_version": "demo-result-v1",
    }, sort_keys=True)
    estimated = math.ceil(len(request_context.encode("utf-8")) / 4)
    allowed = estimated <= DEMO_MAX_INPUT_TOKENS and DEMO_MAX_CALLS >= 1
    result = {
        "budget_policy": "demo-only-character-estimate-v1",
        "mode": "simulated",
        "network_calls": 0,
        "estimated_input_tokens": estimated,
        "max_input_tokens": DEMO_MAX_INPUT_TOKENS,
        "reserved_output_tokens": DEMO_MAX_OUTPUT_TOKENS,
        "max_model_calls": DEMO_MAX_CALLS,
        "calls_reserved": 1 if allowed else 0,
        "within_budget": allowed,
        "provider_price": None,
        "spend_estimation": "Not calculated; no real provider call or billing occurs.",
        "input_manifest_run_id": manifest["run_id"],
    }
    save_json(root / "budget-decision.json", result)
    write_summary("4 · Budget preflight", [
        "- **Decision:** " + ("ALLOW one simulated call" if allowed else "DENY"),
        f"- Character-based input estimate: **{estimated} / {DEMO_MAX_INPUT_TOKENS} demo tokens**",
        f"- Output reservation: {DEMO_MAX_OUTPUT_TOKENS} demo tokens; maximum calls: {DEMO_MAX_CALLS}",
        "- This is a deterministic demonstration estimate, not Anthropic token counting, a price quote, or a real reservation.",
        "- No network request is made.",
    ])
    if not allowed:
        raise SystemExit("Demo budget preflight rejected the selected evidence package.")


def mock_model(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    analysis = load_json(root / "analysis.json")
    package = load_json(root / "evidence-package.json")
    budget_decision = load_json(root / "budget-decision.json")
    available = {item["evidence_id"] for item in package["items"]}
    observations = analysis["static_analysis"].get("observations", [])
    classes = {item["classification"] for item in observations}
    requirements = analysis["requirements"]
    req_class = requirements[0]["classification"] if requirements else "unspecified"
    scenario = manifest["comparison"]

    outcome = "inconclusive"
    rationale = "The available source evidence does not establish the comparison outcome."
    limitation = "More call-path or requirement evidence is needed to determine the behavior."
    if not budget_decision.get("within_budget"):
        rationale = "The simulated budget gate did not admit the assessment."
        limitation = "Assessment was not admitted by the budget gate."
    elif scenario == "code-diff":
        if "synchronous_provider_call" in classes:
            outcome = "supported_deviation"
            rationale = "The AST identifies a direct provider-style call in the request handler, which conflicts with the accepted ADR constraint."
            limitation = ""
        elif "async_enqueue" in classes:
            outcome = "no_deviation_found"
            rationale = "The parsed handler enqueues the work and returns the job identifier; this bounded source excerpt does not establish a synchronous provider call."
            limitation = ""
    elif scenario == "technical-spec":
        if req_class == "synchronous":
            outcome = "supported_deviation"
            rationale = "The extracted specification requirement calls for synchronous provider execution, contrary to the accepted ADR constraint."
            limitation = ""
        elif req_class == "asynchronous":
            outcome = "no_deviation_found"
            rationale = "The extracted requirement routes assessment work through the asynchronous workflow, consistent with the accepted ADR."
            limitation = ""
    elif scenario == "spec-vs-implementation":
        if req_class == "asynchronous" and "synchronous_provider_call" in classes:
            outcome = "supported_deviation"
            rationale = "The specification requires asynchronous assessment work, but the implementation calls the provider directly from the handler."
            limitation = ""
        elif req_class == "asynchronous" and "async_enqueue" in classes:
            outcome = "no_deviation_found"
            rationale = "The handler enqueues assessment work as required by the technical specification."
            limitation = ""

    wanted: list[str] = []
    if "EV-ADR-001" in available:
        wanted.append("EV-ADR-001")
    for eid in ("EV-AST-001", "EV-SPEC-001", "EV-DIFF-001"):
        if eid in available:
            wanted.append(eid)
    candidate = {
        "outcome": outcome,
        "rationale": rationale,
        "limitations": [limitation] if limitation else [],
        "evidence_ids": wanted,
        "severity": "not_assigned_by_demo",
        "requires_human_review": True,
    }
    result = {
        "provider": "deterministic-mock",
        "model_id": "mock-llm-fixture-v1",
        "prompt_version": "demo-assessment-v1",
        "output_schema_version": "demo-result-v1",
        "network_requests": 0,
        "input_mode": "evidence-package-only; test oracle excluded",
        "candidate": candidate,
        "explanation": "This output is generated by a small deterministic ruleset to demonstrate the model boundary and structured response shape. It is not an actual LLM response.",
    }
    save_json(root / "mock-model-response.json", result)
    write_summary("5 · Mock model assessment", [
        "- **Provider:** `deterministic-mock` · **Model fixture:** `mock-llm-fixture-v1`",
        f"- **Candidate outcome:** `{outcome}`",
        f"- **Cited evidence IDs:** {', '.join(wanted)}",
        "- The stage reads the evidence package and deterministic analysis. It does not read the test oracle and makes zero network calls.",
        f"- Rationale: {rationale}",
    ])


def validate(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    package = load_json(root / "evidence-package.json")
    model = load_json(root / "mock-model-response.json")
    oracle = load_json(root / "test-oracle.json")
    analysis = load_json(root / "analysis.json")
    source_by_id = {item["artifact_id"]: item for item in manifest["artifacts"]}
    evidence = package["items"]
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("Evidence IDs are unique", len(evidence_by_id) == len(evidence), "Evidence package IDs must be unique.")
    refs_exist = all(item.get("artifact_id") in source_by_id for item in evidence)
    check("Every evidence item maps to a source artifact", refs_exist, "Artifact IDs must resolve to the pinned input manifest.")
    versions_match = all(
        item.get("artifact_version") == source_by_id.get(item.get("artifact_id"), {}).get("version")
        for item in evidence
    )
    check("Evidence versions match pinned source hashes", versions_match, "No evidence item may cite a different or unknown version.")
    candidate = model.get("candidate", {})
    valid_outcomes = {"supported_deviation", "no_deviation_found", "inconclusive"}
    check("Outcome is in the result contract", candidate.get("outcome") in valid_outcomes, "Candidate outcome must be a documented domain result.")
    cited = candidate.get("evidence_ids", [])
    refs_resolve = bool(cited) and all(eid in evidence_by_id for eid in cited)
    check("Every model citation resolves", refs_resolve, "All cited IDs must exist in the exact evidence package.")
    mode = manifest["comparison"]
    if candidate.get("outcome") == "supported_deviation":
        has_adr = any(evidence_by_id.get(eid, {}).get("evidence_type") == "architectural_constraint" for eid in cited)
        support_types = {evidence_by_id.get(eid, {}).get("evidence_type") for eid in cited}
        has_support = bool({"ast_call_site", "technical_requirement"} & support_types)
        check("Deviation cites a governing constraint and technical evidence", has_adr and has_support,
              "A deviation needs both the governing constraint and relevant source evidence.")
    elif candidate.get("outcome") == "no_deviation_found":
        support_types = {evidence_by_id.get(eid, {}).get("evidence_type") for eid in cited}
        if mode in {"code-diff", "technical-spec"}:
            has_constraint = "architectural_constraint" in support_types
            has_source = bool({"ast_call_site", "technical_requirement"} & support_types)
        else:
            has_constraint = "technical_requirement" in support_types
            has_source = "ast_call_site" in support_types
        check("No-deviation result cites bounded comparison evidence", has_constraint and has_source,
              "The result must cite the decision/requirement and the source evidence compared.")
    else:
        check("Inconclusive result explains a limitation", bool(candidate.get("limitations")),
              "An inconclusive result must identify what evidence is missing or unresolved.")

    if "implementation" in source_by_id:
        ast = analysis["static_analysis"]
        ast_ok = ast.get("parse_status") == "parsed" and ast.get("source_sha256") == source_by_id["ART-CODE-001"]["sha256"]
        check("AST pass corresponds to pinned implementation", ast_ok, "AST results must be from the exact code bytes in the manifest.")
    oracle_matches = candidate.get("outcome") == oracle.get("expected_outcome")
    check("Candidate matches selected fixture oracle", oracle_matches,
          f"Expected {oracle.get('expected_outcome')}; got {candidate.get('outcome')}.")

    passed = all(item["passed"] for item in checks)
    result = {
        "validation_version": "1.0.0",
        "status": "passed" if passed else "failed",
        "comparison": manifest["comparison"],
        "sample_case": manifest["sample_case"],
        "candidate_outcome": candidate.get("outcome"),
        "expected_outcome": oracle.get("expected_outcome"),
        "outcome_match": oracle_matches,
        "evidence_items": len(evidence),
        "checks": checks,
    }
    save_json(root / "validation-result.json", result)
    write_summary("6 · Application-side validation", [
        f"- **Validation:** {'PASS' if passed else 'FAIL'}",
        f"- **Expected / actual:** `{result['expected_outcome']}` / `{result['candidate_outcome']}`",
        *[f"- [{'x' if item['passed'] else ' '}] {item['name']}: {item['detail']}" for item in checks],
    ])
    if not passed:
        raise SystemExit("Evidence contract validation or fixture oracle failed.")


def report(args: argparse.Namespace) -> None:
    root = Path(args.output)
    manifest = load_json(root / "input-manifest.json")
    analysis = load_json(root / "analysis.json")
    evidence = load_json(root / "evidence-package.json")
    budget_result = load_json(root / "budget-decision.json")
    model = load_json(root / "mock-model-response.json")
    validation_result = load_json(root / "validation-result.json")
    artifacts = manifest["artifacts"]
    obs = analysis["static_analysis"].get("observations", [])
    lines = [
        "# Functional analysis demo report",
        "",
        f"- **Run:** `{manifest['run_id']}`",
        f"- **Comparison:** `{manifest['comparison']}`",
        f"- **Sample case:** `{manifest['sample_case']}`",
        f"- **Comparison contract:** `{manifest['comparison_contract']}`",
        f"- **Final status:** **{validation_result['status'].upper()}**",
        "",
        "## Pipeline stages",
        "",
        "| Stage | What it did | Result |",
        "|---|---|---|",
        "| 1. Admit and pin inputs | Copied synthetic inputs and SHA-256 versioned them | PASS |",
        f"| 2. Deterministic analysis | Go AST parse + diff scan + Markdown requirement extraction | {len(obs)} AST call site(s), {len(analysis['requirements'])} requirement(s) |",
        f"| 3. Evidence contract | Built version-bound evidence records | {len(evidence['items'])} items |",
        f"| 4. Budget gate | Character-based mock request estimate; no provider call | {'ALLOW' if budget_result['within_budget'] else 'DENY'} ({budget_result['estimated_input_tokens']} estimated input tokens) |",
        f"| 5. Mock model | Deterministic fixture response; no network request | {model['candidate']['outcome']} |",
        f"| 6. Validate | Citation, provenance, outcome contract and fixture oracle | {validation_result['status'].upper()} |",
        "",
        "## Sources pinned for this run",
        "",
        "| Artifact | Role | SHA-256 version | Fixture source |",
        "|---|---|---|---|",
    ]
    for item in artifacts:
        lines.append(f"| `{item['artifact_id']}` | {item['role']} | `{item['version'][:23]}…` | `{item['original_fixture_path']}` |")
    lines += [
        "",
        "## Extracted AST call sites",
        "",
    ]
    if obs:
        lines += ["| Line | Call site | Classification |", "|---:|---|---|"]
        for item in obs:
            lines.append(f"| {item['line']} | `{item['call']}` | `{item['classification']}` |")
    else:
        lines.append("AST was not applicable to this comparison; the document parser handled specification requirements.")
    lines += [
        "",
        "## Evidence package",
        "",
        "| Evidence ID | Type | Source + locator | Fact |",
        "|---|---|---|---|",
    ]
    for item in evidence["items"]:
        locator = f"{item['source_path']}:{item['locator']['line_start']}"
        lines.append(f"| `{item['evidence_id']}` | `{item['evidence_type']}` | `{locator}` | {item['fact']} |")
    lines += [
        "",
        "## Mock model response",
        "",
        f"- **Provider label:** `{model['provider']}`",
        f"- **Model fixture:** `{model['model_id']}`",
        f"- **Prompt version:** `{model['prompt_version']}`",
        f"- **Network requests:** {model['network_requests']}",
        f"- **Candidate outcome:** `{model['candidate']['outcome']}`",
        f"- **Evidence cited:** {', '.join('`'+x+'`' for x in model['candidate']['evidence_ids'])}",
        f"- **Rationale:** {model['candidate']['rationale']}",
        "",
        "> This is a deterministic mock response, not an actual LLM assessment. The budget is a display fixture, not a provider token count or billing estimate.",
        "",
        "## Validation checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in validation_result["checks"]:
        lines.append(f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | {item['detail']} |")
    lines += [
        "",
        "## Artifacts included",
        "",
        "The downloadable workflow artifact includes the exact synthetic input files, source manifest, AST scan, normalized analysis, evidence package, budget decision, mock-model response, validation results, and this report.",
        "",
        "## What this demo proves",
        "",
        "- The user-selected comparison mode determines which inputs are admitted.",
        "- Go source is parsed with `go/parser` / `go/ast`; specs are parsed deterministically.",
        "- Evidence references bind to immutable input hashes and explicit line locators.",
        "- The mock-model output is a candidate, and a separate validator rejects invalid references or outcomes.",
        "- An inconclusive case remains inconclusive when source evidence does not justify a stronger claim.",
        "",
    ]
    report_text = "\n".join(lines)
    (root / "functional-analysis-report.md").write_text(report_text, encoding="utf-8")
    save_json(root / "functional-analysis-report.json", {
        "run_id": manifest["run_id"],
        "comparison": manifest["comparison"],
        "sample_case": manifest["sample_case"],
        "status": validation_result["status"],
        "expected_outcome": validation_result["expected_outcome"],
        "actual_outcome": validation_result["candidate_outcome"],
        "evidence_item_count": len(evidence["items"]),
        "validation_checks": validation_result["checks"],
    })
    write_summary("Functional analysis demo · final report", [
        f"- **Status:** {validation_result['status'].upper()}",
        f"- **Comparison:** `{manifest['comparison']}` / `{manifest['sample_case']}`",
        f"- **Outcome:** `{validation_result['candidate_outcome']}`",
        f"- **Evidence items validated:** {len(evidence['items'])}",
        "- The final artifact contains all intermediate JSON contracts and the Markdown report.",
    ])
    print(f"Report written to {root / 'functional-analysis-report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--comparison", required=True)
    prep.add_argument("--sample-case", required=True)
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--output", required=True)
    prep.set_defaults(func=prepare)
    for command, func in [
        ("analyze", analyze), ("evidence", evidence), ("budget", budget),
        ("mock-model", mock_model), ("validate", validate), ("report", report),
    ]:
        item = sub.add_parser(command)
        item.add_argument("--output", required=True)
        item.set_defaults(func=func)
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
