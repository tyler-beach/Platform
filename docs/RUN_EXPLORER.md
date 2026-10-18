# Pathfinder Run Explorer

The Run Explorer is a live execution-inspection page at `/explore/`. It reads public GitHub Actions run/job/artifact metadata directly from the GitHub REST API. It does not embed a token in the static site. For private repository data, use an authenticated service or authorized GitHub UI rather than adding credentials to browser code.

## Views

- **Run history:** filter and select an actual workflow run by title, workflow, branch, revision, or run ID.
- **Attempt picker:** inspect a specific rerun attempt without silently switching to the latest one.
- **Signal flow and step inspector:** move between jobs/steps and inspect status, start/end times, duration, and parent-job context.
- **Logs:** retrieve and unpack the job's real log archive in-browser where the public API/CORS policy permits it. The panel prefers step-numbered log files. If filenames cannot be mapped reliably, it clearly shows that it is falling back to the parent job's archive.
- **Inputs:** display allowlisted values from an actual input manifest. GitHub's step summary endpoint does not expose resolved action input values, so missing values remain missing rather than being inferred.
- **Artifacts:** inspect uploaded ZIP bundles in the browser, preview JSON files, show source files as text, and compute SHA-256 for individual files where Web Crypto is available.
- **Compare executions:** compare two runs or attempts by job and step name, outcome, elapsed time, revision, and artifact inventory. When both corresponding artifact bundles are inspected, compare files by path and SHA-256 (or exact text fallback). Size-only comparison is never presented as content equality.

## Run manifest contract

The PoC Analysis workflow writes `pathfinder-run-manifest.json` into the same artifact bundle as its output. Schema: `pathfinder.execution-manifest/v1`.

The manifest includes:
- GitHub repository/run/attempt/workflow/event/ref/commit metadata.
- An allowlist of explicit workflow-dispatch parameters (comparison mode, language, paths, provider selection, root function, and configured budget limits).
- A list of generated output file paths, byte lengths, and SHA-256 digests.
- An explicit evidence boundary: this is execution provenance, not an ADR compliance verdict.

Secrets, raw environment dumps, source content, prompts, and provider responses are deliberately excluded from the manifest. Logs and evidence bundles remain separate artifacts with their own retention/access controls.

The Functional Analysis Demo already emits `input-manifest.json`, pinned fixture hashes, and separate stage bundles. These are readable through the same artifact inspector.

## Comparison semantics

Jobs are paired by reported job name, steps by reported step name within a job, and output bundles by artifact name after removing a trailing run ID/attempt suffix. Outcome changes, missing/added steps, and timing shifts are separate categories. Timing differences are descriptive signals rather than regressions by themselves. Artifact file comparison is based on file names and hashes when both bundles have been read; a matching byte size alone does not prove matching content.

## Limitations and safety

- This is a static public-site view. Public run history may be rate-limited and data may become unavailable after log/artifact retention expires.
- GitHub's step API does not expose arbitrary step output values, shell variables, or input values. Those must be deliberately written as bounded artifacts by the workflow.
- Large artifacts and logs are truncated only in display previews; downloadable artifacts remain the canonical full copy.
- A workflow's successful status is not evidence that an ADR is satisfied. The UI reports execution state and artifact provenance, while compliance evaluation must be represented in an evidence-linked output.
