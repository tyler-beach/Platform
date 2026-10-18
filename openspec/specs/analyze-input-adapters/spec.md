# analyze-input-adapters Specification

## Purpose
TBD - created by archiving change github-input-adapters. Update Purpose after archive.
## Requirements
### Requirement: Resolve a same-repo pull request into a pinned package

When a Pathfinder analyze issue includes a same-repository pull request reference and valid attestation, intake MUST resolve the PR head commit SHA, fetch **changed** text files within size and count caps, skip denylisted secret-bearing paths (recording limitations), and produce a pinned `pathfinder-evidence-package-v1` whose code artifacts carry that revision. Tech-spec content MAY be omitted. Binary or oversize files MUST be skipped or rejected per policy without inventing observations.

#### Scenario: Same-repo PR changed files yield pinned package
- **GIVEN** an analyze issue with attestation and a same-repo PR URL or number
- **WHEN** the intake adapter runs
- **THEN** the package pins code artifact revisions to the PR head SHA
- **AND** changed text files within caps are present as code artifacts or an explicit limitation lists skips

#### Scenario: Fork or cross-repo PR fails closed
- **GIVEN** a PR from a fork or a repository that is not `github.repository`
- **WHEN** the intake adapter runs
- **THEN** no package evaluation succeeds
- **AND** an error comment explains the denial

#### Scenario: Denylisted paths are skipped not fatal
- **GIVEN** a same-repo PR whose changed files include a denylisted path such as `.env`
- **WHEN** the intake adapter runs
- **THEN** that path is omitted from code artifacts
- **AND** limitations record the skip
- **AND** evaluation may still proceed on remaining files

#### Scenario: Oversize PR payload fails closed
- **GIVEN** a PR whose fetchable text content exceeds configured total byte or file-count caps
- **WHEN** the intake adapter runs
- **THEN** evaluation does not invent observations
- **AND** an error comment describes the cap rejection

### Requirement: Issue form does not accept multi-file bundles

Unaided multi-file submission MUST use the PR adapter. The issue form MUST NOT require or define a multi-file zip or multi-path bundle section for M2; paste remains tech-spec plus at most one sample code field (plus optional full package JSON).

#### Scenario: Multi-file via PR only
- **GIVEN** a collaborator needs multiple source files evaluated
- **WHEN** they use Pathfinder analyze
- **THEN** the supported path is a same-repo PR reference
- **AND** the issue form single sample-code field remains for small pastes only

