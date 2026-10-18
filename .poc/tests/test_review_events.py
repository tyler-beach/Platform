from __future__ import annotations

import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_sampling.review_events import append_event, read_events, GENESIS


def event(event_id="rev-1", **updates):
    base = {
        "event_id": event_id,
        "event_type": "review.dispositioned",
        "unit_id": "unit-adr12-commitabc-run42",
        "analysis_run_id": "run-42",
        "analysis_version": "pipeline-v3+source-sha256:abc123",
        "actor_id": "reviewer:team-appsec",
        "timestamp": "2026-10-18T12:30:00Z",
        "disposition": "needs_more_evidence",
        "reason_code": "missing_runtime_evidence",
        "evidence_refs": ["EV-REQ-1", "EV-OBS-4"],
        "rationale_summary": "Static evidence is present; deployment/runtime state is not established.",
    }
    base.update(updates)
    return base


class ReviewEventLedgerTests(unittest.TestCase):
    def test_appends_hash_chained_events_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-events.jsonl"
            first = append_event(path, event())
            second = append_event(path, event("rev-2", disposition="confirmed_deviation",
                                              reason_code="evidence_supports_claim",
                                              supersedes_event_id="rev-1"))
            rows = read_events(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["event_id"], "rev-1")
            self.assertEqual(rows[0]["disposition"], "needs_more_evidence")
            self.assertEqual(rows[1]["previous_event_hash"], first["event_hash"])
            self.assertEqual(second["previous_event_hash"], first["event_hash"])
            self.assertEqual(rows[0]["previous_event_hash"], GENESIS)

    def test_duplicate_event_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-events.jsonl"
            append_event(path, event())
            with self.assertRaisesRegex(ValueError, "duplicate event_id"):
                append_event(path, event())

    def test_superseding_event_must_reference_existing_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-events.jsonl"
            with self.assertRaisesRegex(ValueError, "superseded event not found"):
                append_event(path, event(supersedes_event_id="missing"))

    def test_missing_analysis_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "analysis_version"):
                append_event(Path(tmp) / "events.jsonl", event(analysis_version=""))

    def test_raw_source_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "raw content fields"):
                append_event(Path(tmp) / "events.jsonl", event(source_excerpt="secret source text"))

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, event())
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["rationale_summary"] = "tampered"
            path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "event hash mismatch"):
                read_events(path)

    def test_invalid_disposition_and_timezone_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            with self.assertRaisesRegex(ValueError, "unsupported disposition"):
                append_event(path, event(disposition="compliant"))
            with self.assertRaisesRegex(ValueError, "include a timezone"):
                append_event(path, event(timestamp="2026-10-18T12:30:00"))


if __name__ == "__main__":
    unittest.main()
