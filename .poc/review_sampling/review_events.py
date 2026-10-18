"""Append-only human review events for offline Pathfinder prototypes.

This JSONL ledger is a local demonstration artifact, not a multi-tenant production
store. It stores references and concise rationales, never source excerpts/prompts.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
EVENT_TYPES = {"review.dispositioned", "review.adjudicated"}
DISPOSITIONS = {
    "confirmed_deviation",
    "false_positive",
    "aligned_confirmed",
    "missed_deviation",
    "inconclusive_correct",
    "needs_more_evidence",
    "cannot_review",
}
REASON_CODES = {
    "evidence_supports_claim",
    "incorrect_adr",
    "out_of_scope",
    "valid_exception",
    "incorrect_observation",
    "invalid_inference",
    "missing_counter_evidence",
    "stale_or_wrong_locator",
    "missing_runtime_evidence",
    "conflicting_requirements",
    "reviewer_disagreement",
    "insufficient_context",
    "other",
}
FORBIDDEN_CONTENT_FIELDS = {
    "source_excerpt", "raw_prompt", "prompt", "source_text", "raw_source",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def event_digest(event_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(event_without_hash).encode("utf-8")).hexdigest()


def _validate_timestamp(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be an ISO-8601 string with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")


def validate_event(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")
    forbidden = FORBIDDEN_CONTENT_FIELDS & payload.keys()
    if forbidden:
        raise ValueError(f"raw content fields are prohibited: {', '.join(sorted(forbidden))}")
    required = {
        "event_id", "event_type", "unit_id", "analysis_run_id",
        "analysis_version", "actor_id", "timestamp", "disposition",
        "reason_code", "evidence_refs", "rationale_summary",
    }
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    for field in ("event_id", "unit_id", "analysis_run_id", "analysis_version", "actor_id"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if payload["event_type"] not in EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {payload['event_type']!r}")
    if payload["disposition"] not in DISPOSITIONS:
        raise ValueError(f"unsupported disposition: {payload['disposition']!r}")
    if payload["reason_code"] not in REASON_CODES:
        raise ValueError(f"unsupported reason_code: {payload['reason_code']!r}")
    _validate_timestamp(payload["timestamp"])
    if not isinstance(payload["evidence_refs"], list) or any(
        not isinstance(ref, str) or not ref.strip() for ref in payload["evidence_refs"]
    ):
        raise ValueError("evidence_refs must be a list of non-empty evidence IDs")
    if len(payload["evidence_refs"]) != len(set(payload["evidence_refs"])):
        raise ValueError("evidence_refs must not contain duplicates")
    if not isinstance(payload["rationale_summary"], str) or not payload["rationale_summary"].strip():
        raise ValueError("rationale_summary must be a concise, non-empty explanation")
    supersedes = payload.get("supersedes_event_id")
    if supersedes is not None and (not isinstance(supersedes, str) or not supersedes.strip()):
        raise ValueError("supersedes_event_id must be a non-empty event ID when supplied")


def read_events(path: str | Path) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_hash = GENESIS
    for line_number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank ledger line at {line_number}")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at ledger line {line_number}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"ledger line {line_number} is not an object")
        expected_prev = event.pop("previous_event_hash", None)
        expected_hash = event.pop("event_hash", None)
        if expected_prev != previous_hash:
            raise ValueError(f"event chain broken at ledger line {line_number}")
        actual_hash = event_digest({**event, "previous_event_hash": expected_prev})
        if expected_hash != actual_hash:
            raise ValueError(f"event hash mismatch at ledger line {line_number}")
        if event.get("event_id") in seen_ids:
            raise ValueError(f"duplicate event_id at ledger line {line_number}")
        validate_event(event)
        seen_ids.add(event["event_id"])
        events.append({**event, "previous_event_hash": expected_prev, "event_hash": expected_hash})
        previous_hash = expected_hash
    return events


def append_event(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and append one immutable review event, returning its chain hashes."""
    validate_event(payload)
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_suffix(ledger.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = read_events(ledger)
        if any(event["event_id"] == payload["event_id"] for event in current):
            raise ValueError(f"duplicate event_id: {payload['event_id']}")
        supersedes = payload.get("supersedes_event_id")
        if supersedes and not any(event["event_id"] == supersedes for event in current):
            raise ValueError(f"superseded event not found: {supersedes}")
        previous_hash = current[-1]["event_hash"] if current else GENESIS
        body = {**payload, "previous_event_hash": previous_hash}
        event = {**body, "event_hash": event_digest(body)}
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(canonical(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        fcntl.flock(lock, fcntl.LOCK_UN)
    return event
