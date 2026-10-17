#!/usr/bin/env python3
"""Optional Bedrock-embedding + Aurora PostgreSQL/pgvector retrieval adapter.

All AWS access uses the caller's AWS SDK credential chain. Database values are bound
parameters; credentials and embeddings are never written to the report.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from retrieval import build_query, sha

EMBEDDING_DIMENSIONS = 1024

SEARCH_SQL = """
SELECT
    chunk_id, adr_id, adr_version, title, chunk_text, normative_text, owner, status, review_state,
    effective_from, effective_until, repositories, services, domains, languages, tags, deviation_check,
    source_path, source_sha256, embedding_model_id, embedding_input_sha256, embedding_dimensions,
    1.0 - (embedding <=> %(query_embedding)s::vector) AS similarity
FROM adr_chunks
WHERE status IN ('accepted', 'approved', 'active')
  AND review_state IN ('current', 'active', 'approved')
  AND (effective_from IS NULL OR effective_from <= now())
  AND (effective_until IS NULL OR effective_until > now())
  AND embedding_model_id = %(embedding_model_id)s
  AND embedding_dimensions = %(embedding_dimensions)s
  AND ('*' = ANY(repositories) OR %(repository)s = ANY(repositories))
  AND ('*' = ANY(services) OR %(service)s = ANY(services))
  AND ('*' = ANY(domains) OR %(domain)s = ANY(domains))
  AND ('*' = ANY(languages) OR lower(%(language)s) = ANY(SELECT lower(x) FROM unnest(languages) AS x))
ORDER BY embedding <=> %(query_embedding)s::vector
LIMIT %(top_k)s
"""



def bedrock_embedding(query: str) -> tuple[list[float], str]:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError(
            "Aurora backend needs optional dependencies: pip install -r .poc/scope/requirements-aws.txt"
        ) from exc

    model_id = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("Set AWS_REGION or AWS_DEFAULT_REGION for Bedrock Runtime")
    if len(query) > 20000:
        raise ValueError("ADR retrieval query is too long; summarize change evidence before embedding")
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": query, "dimensions": EMBEDDING_DIMENSIONS, "normalize": True}),
    )
    payload = json.loads(response["body"].read())
    vector = payload.get("embedding")
    if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSIONS}-dimension embedding from {model_id}; "
            "keep embedding model/dimension consistent with the indexed catalog"
        )
    if any(not isinstance(x, (int, float)) for x in vector):
        raise RuntimeError("Embedding response contains non-numeric vector values")
    return [float(x) for x in vector], model_id


def _connect():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "Aurora backend needs optional dependencies: pip install -r .poc/scope/requirements-aws.txt"
        ) from exc

    host = os.environ.get("ADR_PGHOST") or os.environ.get("PGHOST")
    database = os.environ.get("ADR_PGDATABASE") or os.environ.get("PGDATABASE")
    user = os.environ.get("ADR_PGUSER") or os.environ.get("PGUSER")
    if not host or not database or not user:
        raise RuntimeError("Set ADR_PGHOST, ADR_PGDATABASE, and ADR_PGUSER for Aurora retrieval")

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    auth_mode = os.environ.get("ADR_DB_AUTH", "iam").lower()
    if auth_mode == "iam":
        if not region:
            raise RuntimeError("Set AWS_REGION or AWS_DEFAULT_REGION for Aurora IAM database auth")
        import boto3
        password = boto3.client("rds", region_name=region).generate_db_auth_token(
            DBHostname=host, Port=int(os.environ.get("ADR_PGPORT", "5432")),
            DBUsername=user, Region=region,
        )
    elif auth_mode == "password":
        password = os.environ.get("ADR_PGPASSWORD") or os.environ.get("PGPASSWORD")
        if not password:
            raise RuntimeError("ADR_DB_AUTH=password requires ADR_PGPASSWORD or PGPASSWORD")
    else:
        raise ValueError("ADR_DB_AUTH must be 'iam' or 'password'")

    return psycopg.connect(
        host=host,
        port=int(os.environ.get("ADR_PGPORT", "5432")),
        dbname=database,
        user=user,
        password=password,
        sslmode=os.environ.get("PGSSLMODE", "verify-full"),
        sslrootcert=os.environ.get("PGSSLROOTCERT") or None,
        connect_timeout=int(os.environ.get("ADR_PGCONNECT_TIMEOUT", "5")),
        row_factory=dict_row,
        application_name="adr-deviation-scope-poc",
    )


def retrieve_from_aurora(
    event: dict[str, Any],
    *,
    top_k: int = 5,
    in_scope_threshold: float = 0.55,
    review_threshold: float = 0.43,
) -> dict[str, Any]:
    if top_k < 1 or not 0 <= review_threshold <= in_scope_threshold <= 1:
        raise ValueError("Invalid top-k or similarity thresholds")

    query = build_query(event)
    embedding, model_id = bedrock_embedding(query)
    vector_literal = "[" + ",".join(format(v, ".9g") for v in embedding) + "]"
    params = {
        "query_embedding": vector_literal,
        "repository": str(event.get("repository", "")),
        "service": str(event.get("service", "")),
        "domain": str(event.get("domain", "")),
        "language": str(event.get("language", "*")).lower(),
        "embedding_model_id": model_id,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "top_k": top_k,
    }
    try:
        with _connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(SEARCH_SQL, params)
                rows = cursor.fetchall()
    except Exception as exc:
        # Avoid embedding credentials, SQL parameters, or connection details in output.
        raise RuntimeError(f"Aurora ADR retrieval failed ({type(exc).__name__})") from exc

    def normalize(row: dict[str, Any], lifecycle_gate: str) -> dict[str, Any]:
        row = dict(row)
        score = float(row.pop("similarity"))
        row["version"] = row["adr_version"]
        row["normative_text"] = row.get("normative_text") or row.get("chunk_text") or ""
        for key, value in list(row.items()):
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
        row["score"] = round(score, 4)
        row["backend"] = "aurora_pgvector_bedrock"
        row["tag_matches"] = []
        row["body_matches"] = []
        row["applicability"] = {
            "repository": event.get("repository"),
            "service": event.get("service"),
            "domain": event.get("domain"),
            "language": event.get("language"),
            "gate": lifecycle_gate,
        }
        return row

    candidates = [normalize(row, "eligible_in_sql") for row in rows]
    selected = [x for x in candidates if x["score"] >= in_scope_threshold]
    review = [x for x in candidates if review_threshold <= x["score"] < in_scope_threshold]

    if selected:
        disposition = "in_scope"
        reason = f"{len(selected)} active, metadata-eligible ADR chunk(s) passed the configured vector similarity threshold."
    elif review:
        disposition = "uncertain"
        reason = "Active, metadata-eligible ADRs were retrieved below the in-scope threshold; human review is required."
    else:
        disposition = "not_in_scope"
        reason = "No active, metadata-eligible ADR passed the vector review threshold; this is not proof that no ADR applies."
    return {
        "retrieval_version": "aurora-bedrock-pgvector-v1.0.0",
        "event_id": event.get("case_id", event.get("event_id", "unknown")),
        "query_text": query,
        "query_sha256": sha(query),
        "backend": "aurora_pgvector_bedrock",
        "embedding_model_id": model_id,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "disposition": disposition,
        "reason": reason,
        "thresholds": {"in_scope": in_scope_threshold, "review": review_threshold},
        "selected_adrs": selected,
        "review_candidates": review,
        "candidate_count_after_metadata_filters": len(candidates),
        "excluded_adrs": [],
        "lifecycle_policy": "only accepted/approved/active, current and effective ADR chunks are eligible for ranking",
        "excluded_inactive_or_out_of_scope_count": "excluded by lifecycle/applicability SQL predicates before vector ranking",
        "audit": {
            "query_sha256": sha(query),
            "embedding_model_id": model_id,
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "scoring_note": "1 - cosine distance is a retrieval similarity, not a probability of applicability or deviation.",
            "db_query_sha256": hashlib.sha256(SEARCH_SQL.encode("utf-8")).hexdigest(),
        },
    }
