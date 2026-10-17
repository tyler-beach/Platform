#!/usr/bin/env python3
"""ADR scope candidate retrieval with deterministic local baseline and metadata guardrails."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

STOP = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "change", "changes",
    "code", "do", "does", "for", "from", "had", "has", "have", "if", "in", "into",
    "is", "it", "its", "may", "must", "of", "on", "or", "our", "should", "that",
    "the", "their", "then", "this", "to", "use", "using", "was", "we", "when",
    "which", "will", "with", "without", "work", "new", "update", "updates", "adds",
    "added", "instead", "now", "path", "value", "must", "not",
}
ACTIVE_STATES = {"accepted", "approved", "active"}
RETRIEVAL_VERSION = "scope-retrieval-v1.0.0"


def tokens(text: str) -> set[str]:
    out = set()
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}", text.lower()):
        normalized = token.strip("_-")
        if len(normalized) > 1 and normalized not in STOP:
            out.add(normalized)
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not isinstance(rows, list):
        raise ValueError(f"Expected JSONL: {path}")
    return rows


def _contains(scope_values: list[str], actual: str) -> bool:
    return "*" in scope_values or actual in scope_values


def applicability_gate(adr: dict[str, Any], event: dict[str, Any]) -> tuple[bool, list[str]]:
    """Hard metadata exclusions. Semantic similarity cannot override these."""
    reasons = []
    status = str(adr.get("status", "")).lower()
    review_state = str(adr.get("review_state", "")).lower()
    if status not in ACTIVE_STATES or review_state not in {"current", "active", "approved"}:
        reasons.append(f"inactive lifecycle state: status={status or 'missing'}, review_state={review_state or 'missing'}")
    if not _contains(adr.get("repositories", []), str(event.get("repository", ""))):
        reasons.append("repository is outside ADR repository scope")
    if not _contains(adr.get("services", []), str(event.get("service", ""))):
        reasons.append("service is outside ADR service scope")
    if not _contains(adr.get("domains", []), str(event.get("domain", ""))):
        reasons.append("domain is outside ADR domain scope")
    language = str(event.get("language", "*")).lower()
    language_scope = [str(x).lower() for x in adr.get("languages", [])]
    if not _contains(language_scope, language):
        reasons.append("language is outside ADR language scope")
    return not reasons, reasons


def _relevance(adr: dict[str, Any], query_tokens: set[str]) -> dict[str, Any]:
    tags_text = " ".join(adr.get("tags", []))
    body_text = " ".join([
        str(adr.get("title", "")),
        str(adr.get("normative_text", "")),
        str(adr.get("rationale", "")),
    ])
    tag_tokens = tokens(tags_text)
    body_tokens = tokens(body_text)
    tag_matches = sorted(query_tokens & tag_tokens)
    body_matches = sorted(query_tokens & body_tokens)
    tag_denominator = max(1, min(len(query_tokens), 8))
    body_denominator = max(1, min(len(query_tokens), 15))
    tag_coverage = len(tag_matches) / tag_denominator
    body_coverage = len(body_matches) / body_denominator
    # This is a lexical retrieval ranking, not a semantic probability.
    score = min(1.0, 0.65 * tag_coverage + 0.35 * body_coverage)
    return {
        "score": round(score, 4),
        "tag_matches": tag_matches,
        "body_matches": body_matches,
        "tag_coverage": round(tag_coverage, 4),
        "body_coverage": round(body_coverage, 4),
    }


def build_query(event: dict[str, Any]) -> str:
    fields = [
        event.get("change_summary", ""),
        event.get("diff_summary", ""),
        " ".join(str(x) for x in event.get("normative_requirements", [])),
        " ".join(str(x) for x in event.get("call_edges", [])),
        " ".join(event.get("evidence_terms", [])),
        " ".join(event.get("changed_paths", [])),
    ]
    return "\n".join(str(x) for x in fields if x)


def retrieve(
    event: dict[str, Any],
    catalog: list[dict[str, Any]],
    *,
    top_k: int = 5,
    in_scope_threshold: float = 0.28,
    review_threshold: float = 0.14,
) -> dict[str, Any]:
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if not 0 <= review_threshold <= in_scope_threshold <= 1:
        raise ValueError("thresholds must satisfy 0 <= review <= in-scope <= 1")
    query = build_query(event)
    query_tokens = tokens(query)
    candidates, exclusions, inactive_near_matches = [], [], []
    for adr in catalog:
        eligible, exclusion_reasons = applicability_gate(adr, event)
        if not eligible:
            excluded = {
                "adr_id": adr.get("adr_id"),
                "version": adr.get("version"),
                "title": adr.get("title"),
                "reasons": exclusion_reasons,
            }
            non_lifecycle_exclusions = [x for x in exclusion_reasons if not x.startswith("inactive lifecycle state:")]
            if not non_lifecycle_exclusions and exclusion_reasons:
                inactive_rank = _relevance(adr, query_tokens)
                excluded.update(inactive_rank)
                excluded["lifecycle_near_match"] = inactive_rank["score"] >= review_threshold
                if inactive_rank["score"] >= review_threshold:
                    inactive_near_matches.append(excluded)
            exclusions.append(excluded)
            continue
        rank = _relevance(adr, query_tokens)
        candidates.append({
            "adr_id": adr["adr_id"],
            "version": adr["version"],
            "chunk_id": adr["chunk_id"],
            "title": adr["title"],
            "status": adr["status"],
            "owner": adr.get("owner"),
            "source_path": adr.get("source_path"),
            "source_sha256": adr.get("source_sha256"),
            "normative_text": adr.get("normative_text"),
            "rationale": adr.get("rationale"),
            "deviation_check": adr.get("deviation_check", {}),
            "applicability": {
                "repository": event.get("repository"),
                "service": event.get("service"),
                "domain": event.get("domain"),
                "language": event.get("language"),
                "gate": "eligible",
            },
            **rank,
        })
    candidates.sort(key=lambda x: (-x["score"], x["adr_id"], x["version"]))
    selected = [x for x in candidates if x["score"] >= in_scope_threshold][:top_k]
    review = [x for x in candidates if review_threshold <= x["score"] < in_scope_threshold][:top_k]
    if selected:
        disposition = "in_scope"
        reason = f"{len(selected)} active ADR candidate(s) passed metadata filters and lexical relevance threshold."
    elif review or inactive_near_matches:
        disposition = "uncertain"
        if review and inactive_near_matches:
            reason = "Current ADR candidates are weak and one or more highly similar ADRs are inactive/superseded; human review is required."
        elif inactive_near_matches:
            reason = "A highly similar ADR is inactive or superseded and cannot govern automatically; human review is required."
        else:
            reason = "One or more eligible ADRs have weak lexical support; require review rather than calling them in scope."
    else:
        disposition = "not_in_scope"
        reason = "No active or inactive near-match ADR met the review relevance threshold."
    return {
        "retrieval_version": RETRIEVAL_VERSION,
        "event_id": event.get("case_id", event.get("event_id", "unknown")),
        "query_text": query,
        "query_tokens": sorted(query_tokens),
        "query_sha256": sha(query),
        "backend": "local_lexical_baseline",
        "disposition": disposition,
        "reason": reason,
        "thresholds": {"in_scope": in_scope_threshold, "review": review_threshold},
        "selected_adrs": selected,
        "review_candidates": review,
        "candidate_count_after_metadata_filters": len(candidates),
        "excluded_adrs": exclusions,
        "excluded_inactive_or_out_of_scope_count": len(exclusions),
        "inactive_near_match_count": len(inactive_near_matches),
        "inactive_near_matches": inactive_near_matches,
        "audit": {
            "catalog_chunk_ids": [x.get("chunk_id") for x in catalog],
            "catalog_hash": sha("\n".join(json.dumps(x, sort_keys=True) for x in catalog)),
            "scoring_note": "Lexical ranking is a local stand-in for Bedrock embeddings plus Aurora pgvector retrieval; score is not a calibrated probability.",
        },
    }
