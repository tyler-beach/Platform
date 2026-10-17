#!/usr/bin/env python3
"""Explainable, deterministic evidence-strength score. This is not a calibrated probability."""
from __future__ import annotations
import hashlib
from typing import Any

ALGORITHM_VERSION = "evidence-strength-v2.0.0"
WEIGHTS = {
    "requirement_clarity": 0.20,
    "observation_resolution": 0.25,
    "requirement_observation_linkage": 0.20,
    "evidence_coverage": 0.15,
    "provenance_integrity": 0.10,
    "analysis_completeness": 0.10,
}
STATUS_WEIGHT = {
    "direct": 1.0,
    "resolved": 1.0,
    "resolved_static": 1.0,
    "resolved_approximate": 0.75,
    "external": 0.35,
    "unresolved": 0.20,
    "unresolved_dynamic": 0.20,
}
BANDS = [
    (0.85, "high"),
    (0.70, "substantial"),
    (0.50, "moderate"),
    (0.30, "low"),
    (0.0, "very_low"),
]

def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))

def _component(name: str, score: float, explanation: str, evidence_ids: list[str], details: dict[str, Any] | None = None) -> dict[str, Any]:
    score = round(clamp(score), 4)
    weight = WEIGHTS[name]
    return {
        "dimension": name,
        "score": score,
        "weight": weight,
        "weighted_contribution": round(score * weight, 4),
        "explanation": explanation,
        "evidence_ids": evidence_ids,
        "details": details or {},
    }

def score_assessment(
    *,
    graph: dict[str, Any],
    syntax: dict[str, Any],
    evidence: list[dict[str, Any]],
    artifact_rows: list[dict[str, Any]],
    cited_ids: list[str],
    evidence_links: list[dict[str, Any]],
    proposed_outcome: str,
    coverage_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_by_id = {e.get("evidence_id"): e for e in evidence}
    valid_cites = [evidence_by_id[x] for x in cited_ids if x in evidence_by_id]
    cited_set = set(cited_ids)
    normative = [e for e in evidence if e.get("evidence_type") == "normative_requirement"]
    cited_normative = [e for e in valid_cites if e.get("evidence_type") == "normative_requirement"]
    cited_edges = [e for e in valid_cites if e.get("evidence_type") in {"resolved_call_edge", "unresolved_call_edge"}]
    cited_diffs = [e for e in valid_cites if e.get("evidence_type") == "diff_line"]
    observation_types = {"resolved_call_edge", "unresolved_call_edge", "configuration_property", "source_observation"}
    cited_observations = [e for e in valid_cites if e.get("evidence_type") in observation_types]

    requirement_text = " ".join(e.get("excerpt", "") for e in cited_normative).lower()
    explicit = any(word in requirement_text for word in (
        "must", "shall", "required", "prohibited", "at least", "at most", "no more than",
        "asynchronous", "synchronous", "enqueue", "queue", "non-blocking",
    ))
    if cited_normative and explicit:
        req_score, req_explanation = 0.98, "A cited normative statement contains an explicit, operational execution constraint."
    elif cited_normative:
        req_score, req_explanation = 0.68, "A cited normative statement exists, but the constraint is not classified as operationally specific by this rule set."
    elif normative:
        req_score, req_explanation = 0.35, "Normative requirements were extracted, but the model did not cite any of them."
    else:
        req_score, req_explanation = 0.10, "No auditable normative requirement was extracted; a violation claim cannot be strongly grounded."

    edges_by_id = {e.get("edge_id"): e for e in graph.get("edges", [])}
    functions_by_id = {f.get("symbol_id"): f for f in graph.get("functions", [])}
    path_scores = []
    path_details = []
    for ev in cited_edges:
        edge = edges_by_id.get(ev.get("edge_id"))
        if not edge:
            continue
        caller_id = edge.get("caller_symbol_id")
        caller = functions_by_id.get(caller_id, {})
        prefix_ids = caller.get("entry_path_edge_ids", [])
        chain = [edges_by_id[x] for x in prefix_ids if x in edges_by_id] + [edge]
        if not chain:
            continue
        weights = [STATUS_WEIGHT.get(str(e.get("resolution_status", "unresolved")), 0.2) for e in chain]
        # The weakest link bounds the confidence of this particular call path.
        path_score = min(weights)
        path_scores.append(path_score)
        path_details.append({
            "evidence_id": ev.get("evidence_id"),
            "edge_id": edge.get("edge_id"),
            "callee": edge.get("callee_qualified_name"),
            "path_edge_ids": [e.get("edge_id") for e in chain],
            "edge_statuses": [e.get("resolution_status") for e in chain],
            "path_score": round(path_score, 4),
        })
    # Score only source observations actually cited as support. Call edges use their
    # full entry path; configuration and other direct observations use their own
    # collector resolution status instead of requiring a function graph.
    observation_scores = []
    for ev in cited_observations:
        status = ev.get("resolution_status") or ev.get("resolution", {}).get("status", "unresolved")
        if ev.get("evidence_type") in {"resolved_call_edge", "unresolved_call_edge"} and ev.get("edge_id"):
            continue
        observation_scores.append(STATUS_WEIGHT.get(str(status), 0.20))
    observation_scores.extend(path_scores)
    if path_scores:
        # Multiple cited paths must not hide a weaker path that the model also relies on.
        path_score = min(observation_scores)
        path_explanation = "Based on cited observations; call paths are bounded by their least-certain edge, and direct facts use their collector resolution status."
    elif observation_scores:
        path_score = min(observation_scores)
        path_explanation = "Based on the resolution status of the cited source observations; no call graph is required for configuration or runtime evidence."
    else:
        path_score = 0.10
        path_explanation = "No source observation with a usable resolution status was cited."
    if any(e.get("resolution_status") in {"unresolved", "unresolved_dynamic"} for e in cited_edges):
        path_explanation += " Unresolved/dynamic cited edges do not count as proven call targets."

    cites_valid = len(cited_ids) == len(set(cited_ids)) and all(x in evidence_by_id for x in cited_ids)
    has_observation_support = bool(cited_observations)
    has_diff_support = bool(cited_diffs)
    if cited_normative and has_observation_support:
        coverage_score = 1.0
        coverage_explanation = "Citations include normative requirement evidence and source observations."
    elif cited_normative and has_diff_support:
        coverage_score = 0.85
        coverage_explanation = "Citations include normative requirements and changed-line evidence, but do not include call-graph evidence."
    elif cited_normative or has_observation_support or has_diff_support:
        coverage_score = 0.55
        coverage_explanation = "Some evidence is cited, but at least one material evidence category is missing."
    else:
        coverage_score = 0.15
        coverage_explanation = "The candidate does not cite a combination of requirements and observed behavior."
    if not cites_valid:
        coverage_score = min(coverage_score, 0.10)
        coverage_explanation += " Citation integrity failed: duplicate or unknown evidence IDs are present."

    # Require explicit, typed links between a normative requirement and observed behavior.
    valid_links = []
    invalid_links = []
    for link in evidence_links:
        req_id = link.get("requirement_evidence_id")
        obs_id = link.get("observation_evidence_id")
        req_ev = evidence_by_id.get(req_id)
        obs_ev = evidence_by_id.get(obs_id)
        relation = link.get("relationship")
        valid = (
            req_ev is not None and req_ev.get("evidence_type") == "normative_requirement"
            and obs_ev is not None and obs_ev.get("evidence_type") in observation_types | {"diff_line"}
            and relation in {"contradicts", "consistent_with", "uncertain"}
            and not (relation == "contradicts" and (obs_ev.get("evidence_type") == "unresolved_call_edge" or obs_ev.get("resolution_status") in {"unresolved", "unresolved_dynamic"}))
            and isinstance(link.get("explanation"), str) and bool(link.get("explanation", "").strip())
            and req_id in cited_set and obs_id in cited_set
        )
        if valid:
            valid_links.append({**link, "requirement_type": req_ev.get("evidence_type"), "observation_type": obs_ev.get("evidence_type"), "observation_claim": obs_ev.get("claim", "")})
        else:
            invalid_links.append({"link": link, "reason": "Link must cite a normative requirement and source observation, both included in evidence_ids, with a known relationship and explanation."})
    contradiction_links = [
        x for x in valid_links
        if x.get("relationship") == "contradicts"
        and x.get("observation_type") in observation_types | {"diff_line"}
        and x.get("observation_type") != "unresolved_call_edge"
    ]
    if contradiction_links:
        linkage_score = 0.98
        linkage_explanation = "The model supplied an explicit contradiction link from a cited normative requirement to a cited source observation; the application validated both evidence types and IDs."
    elif valid_links:
        linkage_score = 0.65 if any(x.get("relationship") == "uncertain" for x in valid_links) else 0.55
        linkage_explanation = "Requirement-to-observation links exist, but none explicitly identifies a supported contradiction."
    else:
        linkage_score = 0.10
        linkage_explanation = "No valid explicit link ties a cited normative requirement to the observed behavior."
    if invalid_links:
        linkage_explanation += f" {len(invalid_links)} proposed link(s) failed deterministic validation."
    artifact_ids = {str(x.get("artifact_id")) for x in artifact_rows}
    missing_artifacts = [e.get("evidence_id") for e in valid_cites if not e.get("artifact_id") or str(e.get("artifact_id")) not in artifact_ids]
    bad_excerpt_hashes = [
        e.get("evidence_id") for e in valid_cites
        if e.get("excerpt") is not None and e.get("sha256") != hashlib.sha256(str(e.get("excerpt", "")).encode("utf-8")).hexdigest()
    ]
    if not missing_artifacts and not bad_excerpt_hashes and cites_valid and valid_cites:
        provenance_score = 1.0
        provenance_explanation = "Every cited item resolves to a pinned input artifact and its excerpt SHA-256 matches the stored excerpt."
    elif not valid_cites:
        provenance_score = 0.15
        provenance_explanation = "No valid citation set was available for provenance checks."
    else:
        provenance_score = 0.25 + 0.25 * (1 - len(set(missing_artifacts + bad_excerpt_hashes)) / max(1, len(valid_cites)))
        provenance_explanation = "Some citation provenance checks failed; details identify missing artifact links or excerpt-hash mismatches."

    coverage_reports = coverage_reports or []
    syntax_files = syntax.get("files", [])
    syntax_error_count = sum(len(f.get("errors", [])) for f in syntax_files)
    resolver_diagnostics = graph.get("diagnostics", [])
    root_resolved = graph.get("entry_resolution") == "resolved"
    reachable_edges = graph.get("reachable_edges", [])
    unresolved_count = sum(1 for e in reachable_edges if e.get("resolution_status") in {"unresolved", "unresolved_dynamic"})
    total = max(1, len(reachable_edges))
    if coverage_reports:
        completeness = sum(bool(report.get("complete")) for report in coverage_reports) / len(coverage_reports)
        completeness = 0.20 + 0.75 * completeness
    else:
        completeness = 0.95 if root_resolved else 0.20
    completeness -= min(0.30, syntax_error_count * 0.05)
    completeness -= min(0.25, len(resolver_diagnostics) * 0.05)
    completeness -= 0.20 * (unresolved_count / total)
    completeness = clamp(completeness)
    comp_explanation = (
        f"Entry resolved={root_resolved}; complete evidence sources={sum(bool(r.get('complete')) for r in coverage_reports)}/{len(coverage_reports)}; Tree-sitter syntax errors={syntax_error_count}; "
        f"resolver diagnostics={len(resolver_diagnostics)}; unresolved/dynamic reachable edges={unresolved_count}/{len(reachable_edges)}."
    )

    components = [
        _component("requirement_clarity", req_score, req_explanation, [e["evidence_id"] for e in cited_normative],
                   {"cited_normative_count": len(cited_normative), "all_normative_count": len(normative), "explicit_execution_constraint": explicit}),
        _component("observation_resolution", path_score, path_explanation, [e["evidence_id"] for e in cited_observations],
                   {"cited_paths": path_details}),
        _component("requirement_observation_linkage", linkage_score, linkage_explanation,
                   list(dict.fromkeys([x.get("requirement_evidence_id", "") for x in valid_links] + [x.get("observation_evidence_id", "") for x in valid_links])),
                   {"validated_links": valid_links, "invalid_links": invalid_links, "contradiction_link_count": len(contradiction_links)}),
        _component("evidence_coverage", coverage_score, coverage_explanation, [e["evidence_id"] for e in valid_cites],
                   {"covers_normative_requirement": bool(cited_normative), "covers_observation": has_observation_support, "covers_diff": has_diff_support, "citation_ids_valid": cites_valid}),
        _component("provenance_integrity", provenance_score, provenance_explanation, [e["evidence_id"] for e in valid_cites],
                   {"missing_artifact_ids": missing_artifacts, "excerpt_hash_mismatches": bad_excerpt_hashes, "pinned_artifact_count": len(artifact_rows)}),
        _component("analysis_completeness", completeness, comp_explanation, [],
                   {"entry_resolved": root_resolved, "coverage_reports": coverage_reports, "syntax_error_count": syntax_error_count, "resolver_diagnostic_count": len(resolver_diagnostics), "unresolved_reachable_edges": unresolved_count, "reachable_edge_count": len(reachable_edges)}),
    ]
    raw_score = sum(x["weighted_contribution"] for x in components)
    caps = []
    if not cited_normative:
        raw_score = min(raw_score, 0.49)
        caps.append("No cited normative requirement: score capped at 0.49.")
    if not observation_scores:
        raw_score = min(raw_score, 0.49)
        caps.append("No resolved cited source observation: score capped at 0.49.")
    if not cites_valid or missing_artifacts or bad_excerpt_hashes:
        raw_score = min(raw_score, 0.39)
        caps.append("Citation/provenance validation failed: score capped at 0.39.")
    if proposed_outcome == "supported_deviation" and not (cited_normative and has_observation_support and contradiction_links):
        raw_score = min(raw_score, 0.49)
        caps.append("A supported-deviation claim must cite a normative requirement, source observation, and validated contradiction link: score capped at 0.49.")
    score = round(clamp(raw_score), 4)
    band = next(label for threshold, label in BANDS if score >= threshold)
    accepted_outcome = proposed_outcome
    guardrails = []
    if proposed_outcome == "supported_deviation":
        incomplete_sources = [r for r in coverage_reports if not r.get("complete")]
        if incomplete_sources:
            accepted_outcome = "inconclusive"
            guardrails.append("Downgraded to inconclusive: one or more evidence-source coverage reports are incomplete.")
        elif not normative:
            accepted_outcome = "inconclusive"
            guardrails.append("Downgraded to inconclusive: no normative requirement was available.")
        elif not cited_normative or not has_observation_support:
            accepted_outcome = "potential_deviation"
            guardrails.append("Downgraded to potential_deviation: candidate did not cite both the requirement and a source observation.")
        elif not contradiction_links:
            accepted_outcome = "potential_deviation"
            guardrails.append("Downgraded to potential_deviation: no validated relationship explicitly links the requirement to contradictory behavior.")
        elif not observation_scores or path_score < 0.50 or score < 0.60:
            accepted_outcome = "potential_deviation"
            guardrails.append("Downgraded to potential_deviation: observation resolution/provenance/completeness evidence is below the minimum support threshold.")
        elif not cites_valid or missing_artifacts or bad_excerpt_hashes:
            accepted_outcome = "potential_deviation"
            guardrails.append("Downgraded to potential_deviation: evidence IDs or provenance checks failed.")
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "score": score,
        "score_0_to_100": round(score * 100, 1),
        "band": band,
        "is_calibrated_probability": False,
        "proposed_outcome": proposed_outcome,
        "accepted_outcome": accepted_outcome,
        "components": components,
        "caps": caps,
        "guardrails": guardrails,
        "model_self_reported_confidence": None,
        "evidence_links": valid_links,
        "invalid_evidence_links": invalid_links,
        "principle": "Evidence-strength score is a deterministic, explainable support rating, not a probability that the finding is true. Model confidence is recorded separately and does not increase this score.",
    }
