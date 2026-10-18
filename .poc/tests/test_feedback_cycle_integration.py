from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / ".poc" / "review_sampling"
sys.path.insert(0, str(REVIEW))

from github_issue_intake import build_frame, build_issue  # noqa: E402
from review_events import append_event, read_events  # noqa: E402
from sample import build_batch  # noqa: E402
from validate_feedback_cycle import validate_cycle  # noqa: E402
from promote_review_feedback import export_candidates  # noqa: E402


class FeedbackCycleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "catalog_hash": "c" * 64,
            "results": [{
                "event_id": "event-001",
                "event_summary": "Synthetic session configuration change",
                "comparison": {"overall_result": "deviation"},
                "scope": {"disposition": "in_scope", "reason": "Synthetic fixture only"},
                "adr_matches": [{
                    "adr_id": "ADR-SESSION-01",
                    "adr_version": "rev-7",
                    "title": "Session lifetime",
                    "comparison_result": "deviation",
                    "candidate_explanation": "The synthetic observation exceeds the stated limit.",
                    "requirement_evidence": {
                        "evidence_id": "EV-REQ-01",
                        "path": "docs/adr/session.md",
                        "source_sha256": "d" * 64,
                        "artifact_id": "artifact-adr-01",
                    },
                    "adr_source": {"path": "docs/adr/session.md", "sha256": "d" * 64, "chunk_id": "chunk-01"},
                    "source_observations": [{
                        "evidence_id": "EV-OBS-01", "path": "src/session.go", "line": 44,
                        "excerpt_sha256": "e" * 64,
                    }],
                    "evidence_links": [{
                        "link_id": "LINK-01", "requirement_evidence_id": "EV-REQ-01",
                        "relationship": "contradicts", "observation_evidence_id": "EV-OBS-01",
                    }],
                    "control_limitations": "Synthetic fixture; not a production finding.",
                }],
            }],
        }

    def test_sample_issue_ledger_adjudication_candidate_cycle(self):
        frame, details = build_frame(self.report)
        batch = build_batch(frame, seed="integration-seed", per_stratum=1)
        probability = batch["probability_sample"]
        self.assertEqual(len(probability), 1)
        selected = probability[0]
        title, body = build_issue(selected["unit_id"], selected, details[selected["unit_id"]],
                                 "https://github.com/example/repo/actions/runs/123")
        self.assertIn("[Pathfinder review]", title)
        self.assertIn("EV-OBS-01", body)
        self.assertIn("excerpt SHA-256", body)
        self.assertNotIn("raw source text", body.lower())
        self.assertIn("reviewer disposition is not an adjudication", body.lower())

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "review-events.jsonl"
            common = {
                "unit_id": selected["unit_id"],
                "analysis_run_id": "run-synthetic-001",
                "analysis_version": "commit-" + "a" * 40,
                "evidence_refs": ["EV-REQ-01", "EV-OBS-01"],
            }
            append_event(ledger, {
                **common,
                "event_id": "review-disposition-001",
                "event_type": "review.dispositioned",
                "actor_id": "reviewer-a",
                "timestamp": "2026-10-17T12:00:00Z",
                "disposition": "confirmed_deviation",
                "reason_code": "evidence_supports_claim",
                "rationale_summary": "The pinned synthetic observation contradicts the requirement.",
            })
            append_event(ledger, {
                **common,
                "event_id": "review-adjudication-001",
                "event_type": "review.adjudicated",
                "actor_id": "adjudicator-b",
                "adjudicator_id": "adjudicator-b",
                "timestamp": "2026-10-17T13:00:00Z",
                "disposition": "confirmed_deviation",
                "reason_code": "evidence_supports_claim",
                "rationale_summary": "Independent review confirms the synthetic evidence relationship.",
                "adjudication_status": "adjudicated",
                "evaluation_label": "deviation",
                "evaluation_split": "candidate_train",
                "promotion_status": "approved",
                "feedback_route": "evidence_retrieval",
            })
            events = read_events(ledger)
            audit = validate_cycle(events, batch)
            self.assertTrue(audit["valid"], audit["errors"])
            self.assertEqual(audit["disposition_event_count"], 1)
            self.assertEqual(audit["adjudication_event_count"], 1)

            exported = export_candidates(events)
            self.assertEqual(exported["candidate_count"], 1)
            candidate = exported["candidates"][0]
            self.assertEqual(candidate["evaluation_label"], "deviation")
            self.assertEqual(candidate["evaluation_split"], "candidate_train")
            self.assertEqual(candidate["promotion_state"], "candidate_pending_corpus_review")
            self.assertNotIn("source_excerpt", candidate)
            self.assertIn("source_event_hash", candidate)
            self.assertEqual(len(candidate["source_event_hash"]), 64)

    def test_issue_intake_preserves_no_match_as_explicit_review_unit(self):
        report = {"catalog_hash": "f" * 64, "results": [{
            "event_id": "event-no-match", "event_summary": "Synthetic event",
            "comparison": {"overall_result": "uncertain"},
            "scope": {"disposition": "in_scope", "reason": "No candidate returned"},
            "adr_matches": [],
        }]}
        frame, details = build_frame(report)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame[0]["outcome"], "inconclusive")
        unit = next(iter(details))
        self.assertEqual(details[unit]["adr_id"], "NO-APPLICABLE-ADR")
        self.assertEqual(details[unit]["comparison_result"], "uncertain")


if __name__ == "__main__":
    unittest.main()
