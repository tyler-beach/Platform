#!/usr/bin/env python3
"""Small append-only CSV table store for the single-runner PoC."""
from __future__ import annotations
import csv, fcntl, json, os
from pathlib import Path
from typing import Any

SCHEMAS = {
 "runs": ["run_id","started_at","completed_at","github_run_id","repository","comparison","language","source_path","root_function","model_provider","model","result","status","input_hash","workflow_url"],
 "run_events": ["event_id","run_id","timestamp","stage","event_type","status","details_json"],
 "artifacts": ["artifact_id","run_id","role","path","sha256","byte_length","version"],
 "symbols": ["symbol_id","run_id","language","qualified_name","symbol_kind","signature","declared_type","path","start_line","end_line","resolver","resolution_status"],
 "call_edges": ["edge_id","run_id","caller_symbol_id","callee_symbol_id","call_expression","path","line","resolution_status","resolution_basis","dispatch_kind","is_transitive"],
 "evidence": ["evidence_id","run_id","evidence_type","artifact_id","symbol_id","edge_id","claim","excerpt","path","start_line","end_line","sha256"],
 "budget_reservations": ["reservation_id","run_id","provider","model","max_input_tokens","max_output_tokens","estimated_input_tokens","reserved_at","status","actual_input_tokens","actual_output_tokens"],
 "llm_transactions": ["transaction_id","run_id","provider","model","request_id","status","prompt_sha256","input_chars","output_chars","estimated_input_tokens","actual_input_tokens","actual_output_tokens","duration_ms","error","created_at"],
 "findings": ["finding_id","run_id","outcome","confidence","summary","rationale","evidence_ids_json","limitations_json","validation_status","created_at"],
 "confidence_assessments": ["assessment_id","run_id","algorithm_version","proposed_outcome","accepted_outcome","score_0_to_100","score_0_to_1","score_band","calibrated_probability","model_self_reported_confidence","component_scores_json","caps_json","guardrails_json","principle","evidence_ids_json","created_at"],
 "confidence_components": ["component_id","assessment_id","run_id","dimension","score","weight","weighted_contribution","explanation","evidence_ids_json","details_json","algorithm_version","created_at"],
}
class CsvStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        for name, header in SCHEMAS.items():
            path = self.root / f"{name}.csv"
            if not path.exists():
                with path.open("w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(header)
            with path.open("r", newline="", encoding="utf-8") as f:
                actual = next(csv.reader(f), [])
            if actual != header:
                raise ValueError(f"CSV schema mismatch in {path}: {actual!r}")
    def append(self, table: str, row: dict[str, Any]) -> None:
        if table not in SCHEMAS:
            raise ValueError(f"unknown table: {table}")
        fields = SCHEMAS[table]
        unknown = set(row) - set(fields)
        if unknown:
            raise ValueError(f"unknown {table} columns: {sorted(unknown)}")
        values = {}
        for name in fields:
            value = row.get(name, "")
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            values[name] = "" if value is None else str(value)
        path = self.root / f"{table}.csv"
        with (self.root / ".write.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
                writer.writerow(values)
                f.flush()
                os.fsync(f.fileno())
            fcntl.flock(lock, fcntl.LOCK_UN)
    def rows(self, table: str) -> list[dict[str, str]]:
        if table not in SCHEMAS:
            raise ValueError(f"unknown table: {table}")
        with (self.root / f"{table}.csv").open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
