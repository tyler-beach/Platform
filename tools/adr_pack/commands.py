"""validate / scaffold / build commands."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .parse import list_adr_files, parse_adr_markdown
from .sidecar import (
    draft_sidecar,
    is_approved_complete,
    load_sidecar,
    sidecar_path_for,
    write_sidecar,
)

VALUE_TYPES = {
    "numeric_max": "number",
    "numeric_min": "number",
    "resource_present": "boolean",
    "boolean_required": "boolean",
    "set_membership": "string",
    "dependency_forbidden": "string",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_known_predicates(predicates_path: Path | None) -> set[str]:
    if predicates_path is None or not predicates_path.is_file():
        return set()
    data = json.loads(predicates_path.read_text(encoding="utf-8"))
    preds = data.get("predicates", data)
    if isinstance(preds, dict):
        return set(preds)
    return set()


def validate_adrs(adrs_dir: Path) -> tuple[int, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    errors = 0
    for path in list_adr_files(adrs_dir):
        parsed = parse_adr_markdown(path)
        side = load_sidecar(sidecar_path_for(path))
        ready = bool(side and is_approved_complete(side))
        if side is None:
            parsed.warnings.append("no typed sidecar (.md.req.json); run scaffold")
        elif not ready:
            parsed.warnings.append("sidecar present but not approved/complete for build")
        report = {
            "path": str(path),
            "adr_id": parsed.adr_id,
            "errors": parsed.errors,
            "warnings": parsed.warnings,
            "pack_ready": ready,
        }
        reports.append(report)
        errors += len(parsed.errors)
    return errors, reports


def scaffold_adrs(
    adrs_dir: Path,
    *,
    force: bool = False,
    predicates_path: Path | None = None,
    use_heuristics: bool = True,
) -> dict[str, int]:
    known = load_known_predicates(predicates_path)
    written = skipped = 0
    for path in list_adr_files(adrs_dir):
        parsed = parse_adr_markdown(path)
        if parsed.errors and not parsed.decision:
            # still scaffold shell so humans see the gap
            pass
        dest = sidecar_path_for(path)
        existing = load_sidecar(dest)
        if existing and is_approved_complete(existing) and not force:
            skipped += 1
            continue
        if existing and existing.get("approval_state") == "approved" and not force:
            skipped += 1
            continue
        data = draft_sidecar(parsed, known_predicates=known, use_heuristics=use_heuristics)
        write_sidecar(dest, data)
        written += 1
    return {"written": written, "skipped": skipped}


def build_pack(
    adrs_dir: Path,
    out_dir: Path,
    *,
    catalog_id: str = "company-adr-pack",
    base_predicates_path: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_preds: dict[str, Any] = {}
    if base_predicates_path and base_predicates_path.is_file():
        raw = json.loads(base_predicates_path.read_text(encoding="utf-8"))
        base_preds = dict(raw.get("predicates", raw))

    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    new_preds: dict[str, Any] = {}

    for path in list_adr_files(adrs_dir):
        side_path = sidecar_path_for(path)
        side = load_sidecar(side_path)
        if side is None or not is_approved_complete(side):
            skipped.append(path.name)
            continue
        digest = sha256_file(path)
        kind = side["kind"]
        predicate = side["predicate"]
        row = {
            "adr_id": side["adr_id"],
            "adr_revision": f"sha256:{digest}",
            "requirement_id": side["requirement_id"],
            "title": side["title"],
            "domain": side["domain"],
            "lifecycle_status": side["lifecycle_status"],
            "kind": kind,
            "predicate": predicate,
            "subject": side["subject"],
            "decision": side["decision"],
            "approval_state": "approved",
            "approved_by": side.get("approved_by", "human-sidecar-review"),
            "label_status": side.get("label_status", "human_reviewed"),
            "applicability": side["applicability"],
            "source_span": {
                "path": side.get("source_span", {}).get("path", path.as_posix()),
                "excerpt": side.get("decision", "")[:500],
            },
        }
        for opt in ("limit", "approved_set", "forbidden"):
            if opt in side:
                row[opt] = side[opt]
        rows.append(row)
        if predicate not in base_preds and predicate not in new_preds:
            new_preds[predicate] = {
                "collector": "structured_package",
                "compatible_kinds": [kind],
                "description": side["decision"],
                "domains": list(side["applicability"].get("domains") or [side["domain"]]),
                "value_type": VALUE_TYPES.get(kind, "string"),
                "subject_hint": side["subject"],
            }

    if strict and skipped:
        raise SystemExit(
            f"strict build: {len(skipped)} ADR(s) lack approved complete sidecars "
            f"(e.g. {skipped[:3]})"
        )
    if not rows:
        raise SystemExit("build produced zero requirements; approve complete sidecars first")

    all_preds = dict(base_preds)
    all_preds.update(new_preds)
    used = {r["predicate"] for r in rows}
    missing = sorted(used - set(all_preds))
    if missing:
        raise SystemExit(f"missing predicate registry entries: {missing}")

    slim = {"predicates": {k: all_preds[k] for k in sorted(used)}}
    pred_path = out_dir / "predicates.json"
    req_path = out_dir / "requirements.jsonl"
    pred_path.write_text(json.dumps(slim, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with req_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    parts = [
        "predicates.json:" + sha256_file(pred_path),
        "requirements.jsonl:" + sha256_file(req_path),
    ]
    for path in list_adr_files(adrs_dir):
        if path.name in skipped:
            continue
        parts.append(f"adrs/{path.name}:" + sha256_file(path))
    manifest_hash = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    domains = sorted({r["domain"] for r in rows})
    manifest = {
        "schema_version": "pathfinder-catalog-manifest-v1",
        "catalog_id": catalog_id,
        "catalog_mode": "real",
        "version": "0.1.0",
        "requirement_count": len(rows),
        "adr_count": len(rows),
        "domains": domains,
        "manifest_sha256": manifest_hash,
        "label_status": "mixed_or_human_reviewed",
        "skipped_pending_review": skipped,
        "source_adrs": [f"adrs/{r['source_span']['path'].split('/')[-1]}" for r in rows],
    }
    (out_dir / "catalog_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "requirement_count": len(rows),
        "skipped": skipped,
        "manifest_sha256": manifest_hash,
        "out_dir": str(out_dir),
    }
