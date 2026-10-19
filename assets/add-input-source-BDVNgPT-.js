const e=`# How to add an input source

A source adapter must deliver a versioned, provenance-preserving artifact—not just a text blob.

## Contract

1. Define artifact kind, source-system identity, workspace scoping and allowed URI schemes.
2. Define stable Artifact ID and immutable ArtifactVersion ID assignment.
3. Define revision token, raw-content digest and exact bytes covered by the digest.
4. Implement authorization and source-fetch limits: size, time, recursion, network allowlist and decompression.
5. Preserve source location mapping: repository path/line/symbol, document section/anchor, or another explicit locator.
6. Version parser, normalizer and extractor output. Never rewrite prior extraction records in place.
7. Mark integrity/freshness and locator precision. Represent uncertainty explicitly.
8. Test path traversal, malicious content, prompt injection, oversized input, broken encodings and mutable-source races.

## Adapter result

An adapter returns an immutable version reference plus typed metadata and source spans. It does not decide whether an ADR applies or make the final deviation determination.

The evidence layer assigns job-scoped evidence IDs and retains normalized-to-original source mapping. The model receives only relevant, bounded excerpts. Output may reference only evidence IDs minted by the application.

## Required tests

- Same immutable input yields stable normalized metadata.
- Changed content cannot reuse a version identity without a matching digest.
- Source updates during analysis do not silently change the job's source version.
- Cross-workspace retrieval is denied.
- Location mapping and hashes survive parsing/chunking.
- Secrets in source fixtures are redacted from logs.
`;export{e as default};
