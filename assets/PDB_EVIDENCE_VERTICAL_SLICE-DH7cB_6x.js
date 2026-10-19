const e=`# PDB evidence-to-result vertical slice

This offline prototype connects the existing Kubernetes manifest collector to the reusable ADR requirement engine. It does not query a live Kubernetes cluster, determine ADR scope automatically, or interpret natural-language ADR prose.

## Run it

Install the pinned PoC dependencies and evaluate a complete manifest directory:

\`\`\`sh
python -m pip install -r .poc/requirements.txt
python .poc/requirement_engine/evaluate_pdb.py .poc/fixtures/pdb/ --workload checkout --namespace production --revision git:<immutable-revision>
\`\`\`

The manifest directory must contain the complete inventory being evaluated. A missing PDB is a supported deviation only relative to that supplied inventory. Missing workload definitions, malformed YAML, duplicate keys, and unsupported selectors produce an inconclusive result rather than a negative observation.

Use \`--out-of-scope\` only when an upstream scope decision explicitly excludes the workload. The CLI does not infer scope from namespace names.

## Result semantics

- \`no_deviation_found\`: the supplied evidence includes a matching PDB.
- \`supported_deviation\`: a workload was found and no PDB in the parsed inventory selects its labels.
- \`not_applicable\`: the caller explicitly marks the requirement out of scope or the ADR is not accepted.
- \`inconclusive\`: the collector cannot safely establish an observation.

Every result includes a deterministic fingerprint. Accepted evidence includes artifact ID, revision, source path, source SHA-256, and a typed YAML resource or manifest-inventory locator. A collection failure is represented as an evidence gap and never fabricated as an observation.

## Tests

\`\`\`sh
python -m unittest discover -s .poc/tests -p 'test_pdb_vertical_slice.py' -v
python -m unittest discover -s .poc/tests -v
\`\`\`

These are synthetic offline fixtures. A passing test suite establishes behavior for the cases tested; it does not prove live cluster state, complete production coverage, or semantic interpretation of arbitrary ADRs.
`;export{e as default};
