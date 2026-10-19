from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.adr_pack.commands import build_pack, scaffold_adrs, validate_adrs  # noqa: E402
from tools.adr_pack.heuristics import suggest_from_decision  # noqa: E402
from tools.adr_pack.parse import parse_adr_markdown  # noqa: E402
from tools.adr_pack.sidecar import is_approved_complete, load_sidecar, sidecar_path_for  # noqa: E402


GOOD_ADR = """# ADR-ACME-001 — Session TTL maximum

- **Status:** Accepted
- **Domain:** identity
- **Decision owner:** Security Architecture

## Decision

Authenticated session lifetime MUST NOT exceed 600 seconds.

## Notes

Company policy sample.
"""

BAD_ADR = """# ADR-ACME-002 — Incomplete

- **Status:** Proposed

## Context

No decision yet.
"""


class AdrPackTests(unittest.TestCase):
    def test_parse_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            (adrs / "ADR-ACME-001.md").write_text(GOOD_ADR, encoding="utf-8")
            (adrs / "ADR-ACME-002.md").write_text(BAD_ADR, encoding="utf-8")
            parsed = parse_adr_markdown(adrs / "ADR-ACME-001.md")
            self.assertEqual(parsed.adr_id, "ADR-ACME-001")
            self.assertEqual(parsed.domain, "identity")
            self.assertIn("MUST NOT exceed 600", parsed.decision)
            errors, reports = validate_adrs(adrs)
            self.assertGreaterEqual(errors, 1)
            by_name = {Path(r["path"]).name: r for r in reports}
            self.assertTrue(by_name["ADR-ACME-002.md"]["errors"])
            self.assertFalse(by_name["ADR-ACME-001.md"]["errors"])

    def test_heuristic_numeric_max(self) -> None:
        s = suggest_from_decision("Lifetime MUST NOT exceed 600 seconds.")
        self.assertEqual(s["kind"], "numeric_max")
        self.assertEqual(s["limit"], 600)
        self.assertEqual(s["suggestion_source"], "heuristic")
        self.assertNotIn("approval_state", s)

    def test_scaffold_no_overwrite_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            path = adrs / "ADR-ACME-001.md"
            path.write_text(GOOD_ADR, encoding="utf-8")
            stats = scaffold_adrs(adrs)
            self.assertEqual(stats["written"], 1)
            side_path = sidecar_path_for(path)
            side = load_sidecar(side_path)
            assert side is not None
            self.assertEqual(side["approval_state"], "draft")
            self.assertEqual(side["label_status"], "needs_human_typing")
            self.assertEqual(side["kind"], "numeric_max")
            self.assertEqual(side["limit"], 600)
            self.assertEqual(side.get("suggestion_source"), "heuristic")

            side.update(
                {
                    "predicate": "session.ttl_seconds",
                    "subject": "session",
                    "approval_state": "approved",
                    "label_status": "human_reviewed",
                    "approved_by": "tester",
                }
            )
            side_path.write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(is_approved_complete(side))

            stats2 = scaffold_adrs(adrs)
            self.assertEqual(stats2["skipped"], 1)
            self.assertEqual(stats2["written"], 0)
            reloaded = load_sidecar(side_path)
            assert reloaded is not None
            self.assertEqual(reloaded["predicate"], "session.ttl_seconds")

    def test_build_skips_draft_includes_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adrs = root / "adrs"
            out = root / "out"
            adrs.mkdir()
            good = adrs / "ADR-ACME-001.md"
            draft = adrs / "ADR-ACME-002.md"
            good.write_text(GOOD_ADR, encoding="utf-8")
            draft.write_text(
                GOOD_ADR.replace("ADR-ACME-001", "ADR-ACME-002").replace(
                    "Session TTL", "Idle timeout"
                ),
                encoding="utf-8",
            )
            scaffold_adrs(adrs)
            # Approve only first
            side = load_sidecar(sidecar_path_for(good))
            assert side is not None
            side.update(
                {
                    "predicate": "session.ttl_seconds",
                    "subject": "session",
                    "approval_state": "approved",
                    "label_status": "human_reviewed",
                }
            )
            sidecar_path_for(good).write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")

            base_pred = root / "predicates.json"
            base_pred.write_text(
                json.dumps(
                    {
                        "predicates": {
                            "session.ttl_seconds": {
                                "collector": "structured_package",
                                "compatible_kinds": ["numeric_max"],
                                "value_type": "number",
                                "domains": ["identity"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = build_pack(adrs, out, base_predicates_path=base_pred)
            self.assertEqual(result["requirement_count"], 1)
            self.assertIn("ADR-ACME-002.md", result["skipped"])
            lines = (out / "requirements.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertTrue(row["adr_revision"].startswith("sha256:"))
            self.assertEqual(row["approval_state"], "approved")

    def test_claude_suggest_dry_run_and_execute_mock(self) -> None:
        from tools.adr_pack.claude_suggest import suggest_with_claude

        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            path = adrs / "ADR-ACME-001.md"
            path.write_text(GOOD_ADR, encoding="utf-8")
            scaffold_adrs(adrs, use_heuristics=False)

            dry = suggest_with_claude(adrs, dry_run=True, max_calls=3)
            self.assertEqual(dry.dry_run, 1)
            self.assertEqual(dry.called, 0)
            side = load_sidecar(sidecar_path_for(path))
            assert side is not None
            self.assertNotEqual(side.get("suggestion_source"), "claude")

            def fake_transport(endpoint: str, body: dict) -> tuple[dict, str]:
                self.assertEqual(endpoint, "messages")
                self.assertLessEqual(body.get("max_tokens", 0), 350)
                payload = {
                    "model": body["model"],
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "kind": "numeric_max",
                                    "predicate": "session.ttl_seconds",
                                    "subject": "session",
                                    "limit": 600,
                                    "confidence": "high",
                                    "notes": "matches decision",
                                }
                            ),
                        }
                    ],
                    "usage": {"input_tokens": 120, "output_tokens": 40},
                    "id": "msg_test",
                }
                return payload, "req_test"

            live = suggest_with_claude(
                adrs,
                dry_run=False,
                max_calls=3,
                transport=fake_transport,
                use_cache=True,
            )
            self.assertEqual(live.called, 1)
            self.assertEqual(live.updated, 1)
            side2 = load_sidecar(sidecar_path_for(path))
            assert side2 is not None
            self.assertEqual(side2["suggestion_source"], "claude")
            self.assertEqual(side2["approval_state"], "draft")
            self.assertEqual(side2["predicate"], "session.ttl_seconds")
            self.assertEqual(side2["kind"], "numeric_max")
            self.assertEqual(side2["model_suggestion"]["request_id"], "req_test")

            # Cache hit: wipe fields so sidecar needs help again, but fingerprint matches
            side2["predicate"] = ""
            side2["subject"] = ""
            side2["kind"] = ""
            sidecar_path_for(path).write_text(json.dumps(side2, indent=2) + "\n", encoding="utf-8")
            calls = {"n": 0}

            def counting_transport(endpoint: str, body: dict) -> tuple[dict, str]:
                calls["n"] += 1
                return fake_transport(endpoint, body)

            again = suggest_with_claude(
                adrs,
                dry_run=False,
                transport=counting_transport,
                use_cache=True,
            )
            self.assertEqual(calls["n"], 0)
            self.assertEqual(again.skipped_cache, 1)

    def test_claude_suggest_respects_max_calls(self) -> None:
        from tools.adr_pack.claude_suggest import suggest_with_claude

        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            for i in range(3):
                (adrs / f"ADR-ACME-00{i}.md").write_text(
                    GOOD_ADR.replace("ADR-ACME-001", f"ADR-ACME-00{i}"),
                    encoding="utf-8",
                )
            scaffold_adrs(adrs, use_heuristics=False)
            calls = {"n": 0}

            def fake_transport(endpoint: str, body: dict) -> tuple[dict, str]:
                calls["n"] += 1
                return {
                    "model": "mock",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "kind": "boolean_required",
                                    "predicate": f"test.pred.{calls['n']}",
                                    "subject": "x",
                                    "confidence": "low",
                                }
                            ),
                        }
                    ],
                    "usage": {"input_tokens": 50, "output_tokens": 20},
                }, f"r{calls['n']}"

            stats = suggest_with_claude(
                adrs,
                dry_run=False,
                max_calls=1,
                transport=fake_transport,
                use_cache=False,
            )
            self.assertEqual(calls["n"], 1)
            self.assertEqual(stats.called, 1)
            self.assertGreaterEqual(stats.skipped_budget, 1)


if __name__ == "__main__":
    unittest.main()
