# Enable the internal Pages run explorer

The demo site always includes a synthetic walkthrough generated with the offline mock provider. It can also include a bounded projection of real PoC ledger rows when the repository and Pages access checks pass. This runbook configures that path for an organization-owned private or internal repository.

## Prerequisites

- The repository is owned by an organization and has `private` or `internal` visibility.
- The organization uses GitHub Enterprise Cloud. GitHub's access-controlled Pages mode is named **private** and is available for organization-owned private or internal project repositories.
- The PoC uses only synthetic or approved non-production source data. The mock provider is the default and does not need a model API key.
- Actions are allowed to create and deploy GitHub Pages artifacts. The `Documentation` workflow deploy job requests `pages: write` and `id-token: write`; the analysis workflow requests `contents: write` for the `poc-database` branch.

## Configure repository and Pages access

1. Clone this project into the organization repository. Keep the repository private or internal.
2. In **Settings → Pages**, set the build and deployment source to **GitHub Actions**, then select **Private** site visibility. Private Pages access is available to repository readers. Use the unique Pages URL shown by GitHub for the site.
3. In **Settings → Secrets and variables → Actions → Variables**, add the repository variable `PAGES_REAL_RUN_DATA_ENABLED` with the exact value `true`. This is a feature switch, not a secret.
4. Confirm that the GitHub Actions policy permits the repository's `GITHUB_TOKEN` to write contents. The analysis workflow needs that permission to append its CSV snapshot to `poc-database`.

The exporter independently checks the repository owner type, repository visibility, Pages API `public` value, and exact opt-in. It does not clone the ledger until these checks pass. Pull-request runs never enter the real-data export step.

## Run and refresh the site

1. Open **Actions → ADR Deviation PoC Analysis → Run workflow** and select the default branch (`main`). Start with `mock` as the model provider. Use the checked-in fixture first, then select an approved repository path and its ADR/spec/configuration inputs.
2. Wait for the analysis run to finish. The workflow uploads the run bundle and appends its audit CSV rows to `poc-database`.
3. The completion of a default-branch analysis triggers **Documentation**. That workflow checks the private Pages gates, reads the bounded ledger projection, builds the synthetic walkthrough, and deploys the Pages artifact. A manual **Documentation** run on `main` can also refresh the site.
4. Open the private Pages URL while signed in as a repository reader. Select the completed Actions run. The explorer should show **server-verified workflow runs** and a matching **PoC audit record**, including cited evidence, source hashes, observations, confidence and coverage.

## Verify settings and troubleshoot

From an authenticated terminal with `gh` access, check the repository owner/visibility and Pages audience:

~~~sh
gh api repos/ORG/REPO --jq '{visibility,owner_type:.owner.type}'
gh api repos/ORG/REPO/pages --jq '{public,html_url}'
~~~

The expected values are `owner_type: Organization`, `visibility: private` or `internal`, and `public: false`. The site URL returned by the Pages API is the one to use; a private Pages site has its own host.

- If `PAGES_REAL_RUN_DATA_ENABLED` is absent or not exactly `true`, the site stays fixture-only.
- If the opt-in is `true` but the repository is public, user-owned, or Pages is public/unverifiable, the docs build fails before cloning the ledger.
- If an exported row has a missing or mismatched artifact ID, path, evidence hash, or citation, the build fails closed. Repair the source ledger before retrying.
- If the site opens but the static snapshots fail to load, confirm the viewer has repository read access and is using the private Pages URL returned by GitHub.
- If deployment fails, inspect the `Documentation` workflow's Pages job and confirm the `github-pages` environment and Pages Actions source are enabled.

The explorer sends no browser credential to `api.github.com`. Its static snapshot requests use same-origin credentials so GitHub can enforce private Pages access.
