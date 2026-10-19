# Evidence contract

Evidence is the platform's proof layer. Structured model output is not enough: the application must establish that every reference resolves, is fresh enough for the job, and supports or contextualizes the claim.

## Internal EvidenceItem

| Field | Required | Meaning |
|---|---:|---|
| evidenceId | Yes | Application-generated stable ID unique within the job evidence package. |
| jobId | Yes | Parent analysis job. |
| artifactId | Yes | Logical source identity. |
| artifactVersionId | Yes | Exact immutable version read. |
| artifactKind | Yes | Code change, source file, ADR, technical specification, API contract, or configuration. |
| evidenceRole | Yes | `design_assertion` for proposed specification claims or `implementation_fact` for code/config/runtime claims; role is derived from the pinned source adapter and retained as provenance. |
| contentSha256 | When available | Digest of canonical source bytes/version. |
| path | When meaningful | Canonical path relative to known repository/root. |
| startLine, endLine | When line-addressable | One-based inclusive range; both zero only when line addressing does not apply. |
| symbolOrSection | When available | Function/type/symbol/heading/section anchor. |
| locatorPrecision | Yes | EXACT, APPROXIMATE, or UNAVAILABLE. |
| excerptSha256 | If excerpt exists | Digest of exact excerpt bytes under a documented normalization. |
| excerpt | Internal/controlled | Minimum necessary text for review; not for general logs. |
| relationToClaim | After assessment | SUPPORTS, CONTRADICTS, or CONTEXT. |
| retrievalMethod | Yes | Stable method/version: exact ID, metadata, path/symbol, full-text, embedding, deterministic rule, manual. |
| selectionRationale | Yes | Why the item was retained for assessment. |
| sourceIntegrity | Yes | VERIFIED, UNVERIFIED, STALE, or MISMATCH. |
| collectedAt | Yes | UTC timestamp. |

The public Protobuf EvidenceRef exposes references/locations, not full excerpts. Evidence-detail download is not part of the initial public API.

## Rules

1. **Immutable binding:** bind to artifact version/immutable revision, never only a branch name, current URL, or mutable path.
2. **Existence:** validator confirms each finding evidence ID belongs to the exact job package.
3. **Version match:** evidence version matches the job snapshot and location maps to it.
4. **Span consistency:** if line-addressable, startLine is at least 1, endLine is at least startLine, and endLine is within source bounds. Range is inclusive. For non-line-addressable material both line values are zero and an anchor/hash is required where feasible.
5. **Integrity:** recompute/verify hashes when feasible. Each hash identifies whether it covers raw bytes, normalized source, or excerpt.
6. **No fabricated references:** model cannot create evidence IDs, paths, line numbers, decision IDs, requirement IDs or artifact versions. Unknown/mismatched IDs fail validation.
7. **Source fidelity:** maintain normalized/chunked-to-original offset mapping. If exact mapping is impossible, use APPROXIMATE or UNAVAILABLE.
8. **Balanced retrieval:** retain relevant counter-evidence and conflicting decisions. Absence of evidence is not proof of compliance.
9. **Preserve evidence role:** retain whether a claim came from a design assertion or implementation artifact in its provenance. Evaluate all matching observations together once per requirement; conflicting values remain visible as conflicts instead of being hidden by source grouping.
10. **Prompt injection:** evidence is untrusted data. Embedded instructions do not alter policy or authorize tools.
11. **Least data:** send only minimal relevant excerpt to the model. Keep authorization outside the model. Redact sensitive values according to policy without hiding that redaction occurred.
12. **Freshness:** recheck before publication/review when freshness matters. If the source changed, report against the analyzed version and mark revalidation needed.
13. **Deterministic package:** canonical-sort evidence before hashing or prompt construction (for example artifact version, normalized path, range, evidence ID).

## Claim-to-evidence validation

For each finding, validate evidence IDs and versions, authoritative decision/requirement IDs, status/scope and applicability; require suitable source references for actionable deviation claims; check whether included evidence contradicts the claim; ensure rationale points to evidence rather than generic model knowledge; downgrade to POTENTIAL_DEVIATION or INCONCLUSIVE when preconditions fail; persist validator version and result.

A finding need not cite every input. Each factual assertion must be traceable to relevant source material, preserving known counter-evidence.

## Evidence identity

A versioned evidence fingerprint can include workspace, job, artifact version, locator kind, normalized path, inclusive line span, symbol/section, excerpt digest, and retrieval-method version. Actual implementation must use unambiguous canonical serialization (for example canonical JSON or length-prefixed fields), not naive string concatenation. Version this identity separately from finding deduplication fingerprints.

## Review experience

A reviewer should be able to see the source and immutable revision, path/section and span, authorized excerpt/context, integrity status, supporting/contradicting role, and why it matters. Broken/stale references must be labelled; never silently fall back to latest source.

## Minimum tests

- fabricated evidence ID; evidence from another job/workspace;
- wrong artifact version or stale branch head;
- missing source, out-of-range lines, approximate parser mapping;
- excerpt digest mismatch and redaction behavior;
- both supporting and contradicting evidence in one finding;
- stable ordering/hash under randomized map/slice order;
- prompt injection in ADRs, code comments, strings, and spec prose.
