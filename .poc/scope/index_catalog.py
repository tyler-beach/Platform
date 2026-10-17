#!/usr/bin/env python3
"""Validate and index versioned ADR chunks into Aurora pgvector with Bedrock embeddings."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from aurora_backend import EMBEDDING_DIMENSIONS, _connect, bedrock_embedding
from retrieval import load_jsonl

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / ".poc" / "scope" / "adr_catalog.jsonl"
UPSERT_SQL = """
INSERT INTO adr_chunks (
    chunk_id, adr_id, adr_version, title, chunk_text, normative_text, owner,
    status, review_state, repositories, services, domains, languages, tags,
    deviation_check, source_path, source_sha256, effective_from, effective_until,
    embedding_model_id, embedding_dimensions, embedding
) VALUES (
    %(chunk_id)s, %(adr_id)s, %(adr_version)s, %(title)s, %(chunk_text)s,
    %(normative_text)s, %(owner)s, %(status)s, %(review_state)s,
    %(repositories)s, %(services)s, %(domains)s, %(languages)s, %(tags)s,
    %(deviation_check)s::jsonb, %(source_path)s, %(source_sha256)s,
    %(effective_from)s, %(effective_until)s, %(embedding_model_id)s,
    %(embedding_dimensions)s, %(embedding)s::vector
)
ON CONFLICT (chunk_id) DO UPDATE SET
    adr_id = EXCLUDED.adr_id,
    adr_version = EXCLUDED.adr_version,
    title = EXCLUDED.title,
    chunk_text = EXCLUDED.chunk_text,
    normative_text = EXCLUDED.normative_text,
    owner = EXCLUDED.owner,
    status = EXCLUDED.status,
    review_state = EXCLUDED.review_state,
    repositories = EXCLUDED.repositories,
    services = EXCLUDED.services,
    domains = EXCLUDED.domains,
    languages = EXCLUDED.languages,
    tags = EXCLUDED.tags,
    deviation_check = EXCLUDED.deviation_check,
    source_path = EXCLUDED.source_path,
    source_sha256 = EXCLUDED.source_sha256,
    effective_from = EXCLUDED.effective_from,
    effective_until = EXCLUDED.effective_until,
    embedding_model_id = EXCLUDED.embedding_model_id,
    embedding_dimensions = EXCLUDED.embedding_dimensions,
    embedding = EXCLUDED.embedding
"""


def build_embedding_text(row: dict[str, Any]) -> str:
    tags = ", ".join(row.get("tags", []))
    return (
        f"ADR {row['adr_id']} version {row['version']}: {row['title']}\n"
        f"Normative decision:\n{row['normative_text']}\n"
        f"Rationale:\n{row.get('rationale', '')}\n"
        f"Applicability tags: {tags}"
    )


def validate_catalog(catalog: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for row in catalog:
        chunk_id = str(row.get("chunk_id", ""))
        if not chunk_id or chunk_id in seen:
            raise ValueError(f"Missing or duplicate chunk_id: {chunk_id!r}")
        seen.add(chunk_id)
        source_rel = Path(str(row.get("source_path", "")))
        if source_rel.is_absolute() or ".." in source_rel.parts:
            raise ValueError(f"{chunk_id}: source_path must be a relative workspace path")
        source_path = (root / source_rel).resolve()
        if not source_path.is_file() or root.resolve() not in source_path.parents:
            raise ValueError(f"{chunk_id}: source file is missing or outside the workspace")
        source_bytes = source_path.read_bytes()
        actual_hash = hashlib.sha256(source_bytes).hexdigest()
        expected_hash = str(row.get("source_sha256", "")).strip()
        if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) or actual_hash != expected_hash.lower():
            raise ValueError(f"{chunk_id}: source SHA-256 does not match {source_rel.as_posix()}")
        if not row.get("normative_text") or not row.get("title"):
            raise ValueError(f"{chunk_id}: title and normative_text are required")
        if int(row.get("version", 0)) < 1:
            raise ValueError(f"{chunk_id}: ADR version must be a positive integer")
        output.append(row)
    return output


def index_catalog(catalog: list[dict[str, Any]], root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    catalog = validate_catalog(catalog, root)
    if dry_run:
        return {
            "mode": "dry_run",
            "validated_chunks": len(catalog),
            "unique_adrs": len({row["adr_id"] for row in catalog}),
            "catalog_chunk_ids": [row["chunk_id"] for row in catalog],
            "embedding_requests": 0,
            "db_writes": 0,
        }

    import os
    import boto3

    configured_model = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    active_versions: dict[str, int] = {}
    for row in catalog:
        if str(row.get("status", "")).lower() in {"accepted", "approved", "active"}:
            active_versions[row["adr_id"]] = max(active_versions.get(row["adr_id"], 0), int(row["version"]))

    indexed, reembedded, reused, superseded_updates = 0, 0, 0, 0
    with _connect() as conn:
        with conn.cursor() as cursor:
            # If a newer accepted version is part of this manifest, stop older versions
            # from appearing as current. Inactive ADRs with no active successor are untouched.
            for adr_id, current_version in active_versions.items():
                cursor.execute(
                    """UPDATE adr_chunks
                       SET status = 'superseded', review_state = 'superseded',
                           effective_until = COALESCE(effective_until, now())
                       WHERE adr_id = %s AND adr_version < %s
                         AND status IN ('accepted', 'approved', 'active')""",
                    (adr_id, current_version),
                )
                superseded_updates += max(0, cursor.rowcount)

            for row in catalog:
                chunk_text = build_embedding_text(row)
                cursor.execute(
                    "SELECT source_sha256, embedding_model_id, embedding::text AS embedding_text "
                    "FROM adr_chunks WHERE chunk_id = %s",
                    (row["chunk_id"],),
                )
                existing = cursor.fetchone()
                if (
                    existing
                    and str(existing["source_sha256"]).strip() == row["source_sha256"]
                    and existing["embedding_model_id"] == configured_model
                    and existing["embedding_text"]
                ):
                    vector_literal = existing["embedding_text"]
                    model_id = configured_model
                    reused += 1
                else:
                    vector, model_id = bedrock_embedding(chunk_text)
                    if model_id != configured_model:
                        raise RuntimeError("Configured embedding model ID changed during catalog indexing")
                    vector_literal = "[" + ",".join(format(v, ".9g") for v in vector) + "]"
                    reembedded += 1

                status = str(row.get("status", "draft")).lower()
                review_state = str(row.get("review_state", "pending_review")).lower()
                if status in {"accepted", "approved", "active"} and review_state not in {"current", "active", "approved"}:
                    raise ValueError(f"{row['chunk_id']}: active status must use a current/approved review_state")
                params = {
                    "chunk_id": row["chunk_id"],
                    "adr_id": row["adr_id"],
                    "adr_version": int(row["version"]),
                    "title": row["title"],
                    "chunk_text": chunk_text,
                    "normative_text": row["normative_text"],
                    "owner": row.get("owner"),
                    "status": status,
                    "review_state": review_state,
                    "repositories": row.get("repositories", ["*"]),
                    "services": row.get("services", ["*"]),
                    "domains": row.get("domains", ["*"]),
                    "languages": [str(x).lower() for x in row.get("languages", ["*"])],
                    "tags": row.get("tags", []),
                    "deviation_check": json.dumps(row.get("deviation_check", {})),
                    "source_path": str(row["source_path"]),
                    "source_sha256": row["source_sha256"],
                    "effective_from": row.get("effective_from"),
                    "effective_until": row.get("effective_until"),
                    "embedding_model_id": model_id,
                    "embedding_dimensions": EMBEDDING_DIMENSIONS,
                    "embedding": vector_literal,
                }
                cursor.execute(UPSERT_SQL, params)
                indexed += 1
    return {
        "mode": "live",
        "indexed_chunks": indexed,
        "unique_adrs": len({row["adr_id"] for row in catalog}),
        "embedding_requests": reembedded,
        "reused_embeddings": reused,
        "older_versions_superseded": superseded_updates,
        "embedding_model_id": configured_model,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "catalog_chunk_ids": [row["chunk_id"] for row in catalog],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true", help="Validate content hashes and metadata without AWS/DB requests")
    args = parser.parse_args()
    catalog = load_jsonl(args.catalog)
    result = index_catalog(catalog, args.workspace.resolve(), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
