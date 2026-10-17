-- Aurora PostgreSQL + pgvector schema for versioned ADR chunks.
-- Keep chunks immutable by (adr_id, adr_version, chunk_id); a new ADR version inserts new rows.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS adr_chunks (
    chunk_id              text PRIMARY KEY,
    adr_id                text NOT NULL,
    adr_version           integer NOT NULL CHECK (adr_version > 0),
    title                 text NOT NULL,
    chunk_text            text NOT NULL,
    normative_text        text NOT NULL,
    owner                 text,
    status                text NOT NULL CHECK (status IN ('draft', 'proposed', 'accepted', 'approved', 'active', 'superseded', 'rejected', 'retired')),
    review_state          text NOT NULL CHECK (review_state IN ('current', 'active', 'approved', 'superseded', 'retired', 'pending_review')),
    repositories          text[] NOT NULL DEFAULT ARRAY['*']::text[],
    services              text[] NOT NULL DEFAULT ARRAY['*']::text[],
    domains               text[] NOT NULL DEFAULT ARRAY['*']::text[],
    languages             text[] NOT NULL DEFAULT ARRAY['*']::text[],
    tags                  text[] NOT NULL DEFAULT ARRAY[]::text[],
    deviation_check       jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_path           text NOT NULL,
    source_sha256         char(64) NOT NULL,
    effective_from        timestamptz,
    effective_until        timestamptz,
    embedding_model_id    text NOT NULL,
    embedding_input_sha256 char(64) NOT NULL,
    embedding_dimensions  integer NOT NULL DEFAULT 1024 CHECK (embedding_dimensions = 1024),
    embedding             vector(1024) NOT NULL,
    created_at            timestamptz NOT NULL DEFAULT now(),
    CHECK (effective_until IS NULL OR effective_from IS NULL OR effective_until > effective_from),
    UNIQUE (adr_id, adr_version, chunk_id)
);

CREATE INDEX IF NOT EXISTS adr_chunks_embedding_hnsw
    ON adr_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS adr_chunks_scope_repositories_gin ON adr_chunks USING gin (repositories);
CREATE INDEX IF NOT EXISTS adr_chunks_scope_services_gin ON adr_chunks USING gin (services);
CREATE INDEX IF NOT EXISTS adr_chunks_scope_domains_gin ON adr_chunks USING gin (domains);
CREATE INDEX IF NOT EXISTS adr_chunks_scope_languages_gin ON adr_chunks USING gin (languages);
CREATE INDEX IF NOT EXISTS adr_chunks_lifecycle_idx ON adr_chunks (status, review_state, effective_from, effective_until);
CREATE INDEX IF NOT EXISTS adr_chunks_adr_version_idx ON adr_chunks (adr_id, adr_version);

-- Query template (the application uses bound parameters; it does not interpolate user input).
-- Current/approved ADR lifecycle and metadata filters are applied before a candidate can enter
-- model context. Similarity is a ranking feature, not a probability of applicability or violation.
SELECT
    chunk_id, adr_id, adr_version, title, chunk_text, normative_text, owner, status,
    repositories, services, domains, languages, tags, deviation_check,
    source_path, source_sha256,
    1.0 - (embedding <=> %(query_embedding)s::vector) AS similarity
FROM adr_chunks
WHERE status IN ('accepted', 'approved', 'active')
  AND review_state IN ('current', 'active', 'approved')
  AND (effective_from IS NULL OR effective_from <= now())
  AND (effective_until IS NULL OR effective_until > now())
  AND ('*' = ANY(repositories) OR %(repository)s = ANY(repositories))
  AND ('*' = ANY(services) OR %(service)s = ANY(services))
  AND ('*' = ANY(domains) OR %(domain)s = ANY(domains))
  AND ('*' = ANY(languages) OR lower(%(language)s) = ANY(SELECT lower(x) FROM unnest(languages) AS x))
ORDER BY embedding <=> %(query_embedding)s::vector
LIMIT %(top_k)s;
