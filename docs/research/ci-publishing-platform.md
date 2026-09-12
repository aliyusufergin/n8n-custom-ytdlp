# CI/CD & publishing platform facts: GitHub Actions, Docker build actions, Docker Hub, update detection, supply chain

Retrieved: 2026-09-10 (final fetches and live read-only spot checks on 2026-09-11)

Scope: platform facts for automatically building official n8n 2.x image + yt-dlp nightly + ffmpeg, testing it, and publishing multi-arch (linux/amd64 + linux/arm64) to a personal Docker Hub namespace. Facts and trade-offs only; no design decision.

Repo state (supplied by coordinator, not re-verified): `aliyusufergin/n8n-custom-ytdlp` is **public**; Actions enabled, all actions allowed (no SHA-pin policy); default workflow token permissions = read; no branch protection or rulesets; no Actions secrets; local `gh` token scopes `admin:public_key, read:org, repo` (no `workflow`); git pushes use SSH.

---

## Key findings

- **60-day schedule rule applies to this public repo.** "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." The docs don't define "activity" or say whether GITHUB_TOKEN/bot commits count, and no such rule is documented for private repos. [events: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [disable/enable](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
- **Cron is best-effort.** Runs can be delayed under load (worst at the top of the hour) and queued jobs "may be dropped". Schedules run only from the default branch. Minimum interval is 5 min. An IANA `timezone` is supported (with DST handling). [events: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- **Scheduled-run notifications** go to the user who created the workflow. After that they go to whoever last changed the cron line, or to whoever re-enabled a disabled workflow. [notifications](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs)
- **GITHUB_TOKEN events don't start new runs**, except `workflow_dispatch` and `repository_dispatch`. Since 2026-06-11, a PR opened, synchronized or reopened by GITHUB_TOKEN creates runs in an **approval-required** state. A GitHub App token or PAT avoids both limits. [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token), [changelog 2026-06-11](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/)
- **GITHUB_TOKEN cannot modify `.github/workflows/`.** The `permissions:` key list has no `workflows` permission. Classic PATs/OAuth tokens need the `workflow` scope; fine-grained PATs and GitHub Apps need "Workflows: write". No GitHub doc says whether SSH-key pushes are subject to this. [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions), [OAuth scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps), [fine-grained PAT permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
- **Free hosted runners for public repos, including arm64.** Public repos use standard hosted runners free, with `ubuntu-24.04-arm` (4 vCPU/16 GB). Private repos got arm64 standard runners on 2026-01-29, at 2 vCPU/8 GB. They draw on Free's 2,000 included min/month, then cost $0.005/min (arm64) or $0.006/min (x64). [runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [changelog 2026-01-29](https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/), [billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- **2026 Actions pricing.** Hosted-runner prices were cut up to 39% effective 2026-01-01. The announced $0.002/min self-hosted platform fee (planned for 2026-03-01) was **postponed**. Public repos stay free. [changelog 2025-12-16](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/)
- **Docker action majors (latest releases):** `login-action` v4 (v4.6.0), `setup-qemu-action` v4 (v4.3.0), `setup-buildx-action` v4 (v4.3.0), `metadata-action` v6 (v6.2.0), `build-push-action` v7 (v7.3.0), `scout-action` v1 (v1.24.0). There is also a Docker-maintained reusable workflow repo, **`docker/github-builder`** (v1.17.0). (`gh api repos/<repo>/releases/latest`)
- **Docker's multi-platform guidance now points to `docker/github-builder`.** Docker's GitHub Actions multi-platform page now recommends it for native per-platform runners; the hand-written matrix + digest-merge example is no longer on that page. Its default runner mapping sends `linux/arm*` to `ubuntu-24.04-arm`. It signs attestation manifests by default when pushing (`sign: auto`). [Docker multi-platform GHA](https://docs.docker.com/build/ci/github-actions/multi-platform/), [github-builder](https://github.com/docker/github-builder)
- **Default provenance:** `build-push-action` adds **`mode=max` provenance for public repos**, which includes build-arg values, and `mode=min` for private repos. SBOM is off by default. [attestations](https://docs.docker.com/build/ci/github-actions/attestations/)
- **Docker Hub token scopes.** PATs have Read / Write / Delete permissions (API scopes `repo:read`, `repo:write`, `repo:admin`, `repo:public_read`). Pushing needs Write. `peter-evans/dockerhub-description` needs **read/write/delete**. OATs need a Team/Business org. Docker Hub **OIDC login (2026-07-31) is org-only** and not usable from a personal namespace. [PAT](https://docs.docker.com/security/access-tokens/personal-access-tokens/), [Hub API spec](https://docs.docker.com/reference/api/hub/latest/), [dockerhub-description](https://github.com/peter-evans/dockerhub-description), [OAT](https://docs.docker.com/security/access-tokens/organization-access-tokens/), [Docker OIDC](https://www.docker.com/blog/docker-oidc-connections-for-github-actions-available-for-docker-orgs/)
- **Repo auto-creation on push.** `docker push` to a non-existent repo creates it using the namespace's "Default repository privacy" setting (Public/Private; the default value isn't stated). Personal plan: unlimited public repos, **up to 1 private**. [Hub settings](https://docs.docker.com/docker-hub/settings/#configure-default-repository-privacy), [usage](https://docs.docker.com/docker-hub/usage/)
- **Pull limits conflict.** Docs say 100 pulls/6 h unauthenticated (per IPv4 or IPv6 /64) and 200/6 h for authenticated Personal users. The pricing page says Personal gets "100 Docker Hub pulls/hr". A live anonymous HEAD on 2026-09-11 returned `ratelimit-limit: 100;w=3600`. Manifest **HEAD requests don't count**. Multi-arch pulls count once per architecture. [pulls](https://docs.docker.com/docker-hub/usage/pulls/), [pricing](https://www.docker.com/pricing/)
- **Immutable tags exist** (repo settings: all, none, or RE2-regex-selected tags). Immutable tags can't be overwritten or deleted; no plan requirement is stated. [immutable tags](https://docs.docker.com/docker-hub/repos/manage/hub-images/immutable-tags/)
- **Renovate hosted app** (Mend Renovate Community Cloud) is free for unlimited repos. Limits: 1 concurrent job per org, ~4-hourly runs for active repos, 30-min timeout. It handles `ARG`-parameterized `FROM`, has a `docker:disableMajor` preset, pins digests, and can track GitHub releases via regex custom managers (drafts skipped, prereleases marked unstable). [Mend overview](https://docs.renovatebot.com/mend-hosted/overview/), [dockerfile manager](https://docs.renovatebot.com/modules/manager/dockerfile/), [docker](https://docs.renovatebot.com/docker/), [releases adapter source](https://github.com/renovatebot/renovate/blob/main/lib/util/github/graphql/query-adapters/releases-query-adapter.ts)
- **Dependabot** updates Docker `FROM` tags and can ignore `version-update:semver-major`. It does **not** support images referenced via `ARG` in `FROM` (dependabot-core #2057 open; #4597 and #10190 closed as not planned) and has no ecosystem for arbitrary GitHub release binaries. It applies a **default 3-day cooldown** to version updates. [ecosystems](https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories), [options](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference), [#2057](https://github.com/dependabot/dependabot-core/issues/2057)
- **Self-written detection budgets.** GITHUB_TOKEN gets 1,000 REST requests/h per repo; conditional requests returning 304 don't count. The Docker Hub API is per-minute limited (observed 180/min anonymous); registry HEAD doesn't count as a pull. [REST limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [conditional requests](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests), [Hub API](https://docs.docker.com/reference/api/hub/latest/)
- **Supply-chain incidents via moved tags.** GitHub: SHA pinning is "currently the only way to use an action as an immutable release". Actions compromised through moved tags:
  - tj-actions/changed-files, 2025 ([GHSA-mrrh-fwg8-r2c3](https://github.com/advisories/GHSA-mrrh-fwg8-r2c3))
  - reviewdog, 2025 ([GHSA-qmg3-hpqr-gqvc](https://github.com/advisories/GHSA-qmg3-hpqr-gqvc))
  - xygeni-action, March 2026 ([GHSA-f8q5-h5qh-33mh](https://github.com/advisories/GHSA-f8q5-h5qh-33mh))
  - **aquasecurity/trivy-action and setup-trivy, 2026-03-19**: 76/77 tags force-pushed to a credential stealer, plus malicious Trivy Docker Hub images on 2026-03-22 ([GHSA-69fq-xp46-6x23](https://github.com/advisories/GHSA-69fq-xp46-6x23))

  Sources: [secure use](https://docs.github.com/en/actions/reference/security/secure-use).
- **Scanner defaults differ.** Grype's `anchore/scan-action` fails the build by default (severity ≥ medium). `docker/scout-action` is report-only by default (`exit-code: false`). Trivy's README examples set `exit-code: '1'`. [scan-action](https://github.com/anchore/scan-action), [scout-action](https://github.com/docker/scout-action), [trivy-action](https://github.com/aquasecurity/trivy-action)

---

## 1. GitHub Actions

### 1.1 Scheduled workflows

- **Syntax and timing.** POSIX cron, UTC by default, optional IANA `timezone`. For DST zones, skipped spring-forward times "advance to the next valid time". The shortest interval is every 5 minutes. [workflow syntax `on.schedule`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- **Default branch only.** `GITHUB_SHA` is the last commit on the default branch. The run only triggers if the workflow file exists on the default branch. "Scheduled workflows will only run on the default branch." [events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- **Load behavior.** "The `schedule` event can be delayed during periods of high loads… High load times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped. To decrease the chance of delay, schedule your workflow to run at a different time of the hour." [events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- **Inactivity auto-disable.**
  - Public repos only: "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." Scheduled workflows are also disabled by default in forks of public repos. [disable/enable](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
  - Private repos: not mentioned.
  - "Activity" is **not defined**. No GitHub source found on whether commits pushed by `github-actions[bot]` via GITHUB_TOKEN reset the timer. Community discussion [#86087](https://github.com/orgs/community/discussions/86087) has no staff answer.
  - Third-party "keepalive" actions (e.g. [keepalive-workflow](https://github.com/marketplace/actions/keepalive-workflow)) either make a dummy commit or re-enable the workflow via the API. That is their approach, not GitHub policy.
- **Re-enabling.** Via the UI or `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable`. Classic tokens need the `repo` scope; fine-grained tokens need Actions: write. [REST workflows](https://docs.github.com/en/rest/actions/workflows), [fine-grained permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
- **Failure notifications.** "Notifications for scheduled workflows are sent to the user who initially created the workflow." If another user updates the cron syntax, that user gets them. If the workflow is disabled and re-enabled, the re-enabling user gets them. Notifications only arrive if that user has Actions email or web notifications enabled. [notifications](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs)

### 1.2 Events created with GITHUB_TOKEN

- **General rule.** "Events triggered by the `GITHUB_TOKEN` will not create a new workflow run". For example, a push made with GITHUB_TOKEN does not run `on: push` workflows. [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
- **Exceptions.**
  - `workflow_dispatch` and `repository_dispatch` "always create workflow runs".
  - `pull_request` `opened`/`synchronize`/`reopened` from a GITHUB_TOKEN-created or -updated PR creates runs in an **approval-required** state. A user with write access clicks "Approve workflows to run". Other activity types (labeled, edited, closed) create nothing. Announced 2026-06-11. [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token), [changelog](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/)
  - Runs awaiting approval for more than 30 days are deleted. [approve runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)
- **Workarounds.** A GitHub App installation token or a PAT triggers events normally, and PR workflows then run without the approval prompt. [trigger a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
  - Third-party documentation (create-pull-request) says pushing with a deploy key "will trigger `on: push` workflows". [create-pull-request guidelines](https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md)
- **Token lifetime.** At most 6 h on GitHub-hosted runners (the job limit). [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)

### 1.3 Permissions, repo settings, branch protection / rulesets

- **Repo "Workflow permissions" setting.** Choices are "permissive" (read/write for all) or "restricted" (read for `contents` and `packages`). New personal-account repos default to restricted. Workflows are **not** allowed to create or approve PRs by default ("Allow GitHub Actions to create and approve pull requests"). [repo Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- **The `permissions:` key** (workflow- or job-level) adds or removes access relative to the default.
  - Available keys: `actions`, `artifact-metadata`, `attestations`, `checks`, `code-quality`, `contents`, `deployments`, `discussions`, `id-token`, `issues`, `packages`, `pages`, `pull-requests`, `security-events`, `statuses`, `vulnerability-alerts` (new 2026-09-03). There is **no `workflows` key**.
  - Fork PRs typically can't get write access.
  - `pull_request_target` gets a read/write token even from public forks.
  - Sources: [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions), [changelog 2026-09-03](https://github.blog/changelog/2026-09-03-github-actions-early-september-2026-updates/)
- **Needs by task.** Pushing commits or creating releases with GITHUB_TOKEN needs `contents: write`. Opening PRs needs `pull-requests: write`, and the repo setting above must allow Actions to create PRs. OIDC (cosign keyless, attestations) needs `id-token: write`. `actions/attest` needs `id-token: write`, `attestations: write` and `artifact-metadata: write`. [actions/attest](https://github.com/actions/attest)
- **Allowed-actions policy.**
  - An optional repo/org policy "Require actions to be pinned to a full-length commit SHA" also applies to GitHub-authored actions, but "Reusable workflows can still be referenced by tag". [repo Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
  - Blocking with a `!` prefix was added 2025-08-15. [changelog](https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/)
- **Rulesets.** A ruleset can allow bypass for "users with a certain role… specific teams or GitHub Apps". [about rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) This repo has none, so only token permissions gate pushes to `main`.
- **Workflow execution protections** (public preview 2026-06-18) are built on rulesets. Actor rules restrict who can trigger workflows (users, roles, Apps, Copilot, Dependabot). Event rules restrict which events can run. There is an evaluate mode. [changelog](https://github.blog/changelog/2026-06-18-control-who-and-what-triggers-github-actions-workflows/)

### 1.4 Changing files under `.github/workflows/`

- **OAuth `workflow` scope:** "Grants the ability to add and update GitHub Actions workflow files. Workflow files can be committed without this scope if the same file (with both the same path and contents) exists on another branch in the same repository." [OAuth scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
- **Fine-grained PATs:** the "Workflows" repository permission is an additional requirement on `PUT/DELETE /repos/{o}/{r}/contents/{path}`, `POST /git/refs`, `PATCH /git/refs/{ref}`, `POST /releases` and `PATCH /releases/{id}`, when workflow files are involved. [fine-grained permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
- **GitHub Apps:** "If your app specifically needs to access or edit Actions files in the `.github/workflows` directory, request the 'Workflows' repository permission" (applies to HTTP-based Git and the API). [GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)
- **GITHUB_TOKEN** is a GitHub App installation token with no grantable `workflows` permission (see 1.3). The resulting error is "refusing to allow a GitHub App to create or update workflow … without `workflows` permission". [community #27072](https://github.com/orgs/community/discussions/27072) (error text only).
- **Releases:** classic OAuth/PAT tokens also need `workflow` when the release's target commit changes workflow files relative to the default branch (2023-11-02). [changelog](https://github.blog/changelog/2023-11-02-github-actions-enforcing-workflow-scope-when-creating-a-release/)
- **gh CLI:** minimum token scopes are `repo`, `read:org`, `gist`; more via `--scopes`. [gh auth login](https://cli.github.com/manual/gh_auth_login)
  - With the local token (no `workflow`), gh or API calls that create or update workflow files will be refused. HTTPS git pushes through gh's credential helper that touch workflow files are also affected: the scope is defined for OAuth/PAT tokens.
  - `gh workflow run/enable/disable` use Actions endpoints; classic tokens need `repo` scope. [REST workflows](https://docs.github.com/en/rest/actions/workflows)
- **SSH:** no GitHub documentation found stating SSH-key git pushes are subject to the `workflow` scope; SSH keys carry no OAuth scopes. Deploy keys with write access "can perform the same actions as … a collaborator on a personal repository". [deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys) Treat as undocumented (see Uncertainties).

### 1.5 Hosted runners and billing

| Label (standard runners) | Public repo spec | Private repo spec |
|---|---|---|
| `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04` (26.04 public preview) | x64, 4 CPU / 16 GB / 14 GB SSD | x64, 2 CPU / 8 GB / 14 GB |
| `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `ubuntu-26.04-arm` (26.04 preview) | arm64, 4 CPU / 16 GB / 14 GB | arm64, 2 CPU / 8 GB / 14 GB |
| `ubuntu-slim` | x64, 1 CPU / 5 GB; 15-min job timeout | same |

Source: [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

- **arm64 history.**
  - Public repos: preview 2025-01-16 ([changelog](https://github.blog/changelog/2025-01-16-linux-arm64-hosted-runners-now-available-for-free-in-public-repositories-public-preview/)), GA 2025-08-07 ([changelog](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/)).
  - Private repos: since 2026-01-29; "usage counts towards the free minutes included in your plan". [changelog](https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/)
- **Billing.** "GitHub Actions usage is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners." [billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
  - Private-repo included usage: GitHub Free 2,000 min/month, 500 MB artifacts, 10 GB cache per repo. Pro: 3,000 min.
  - Per-minute rates: Linux 1-core x64 $0.002; Linux 2-core x64 $0.006; **Linux 2-core arm64 $0.005**; Windows 2-core $0.010. Cache beyond 10 GB costs $0.07/GB-month.
- **2026 pricing changes.** Hosted-runner prices dropped up to 39% effective **2026-01-01**. A $0.002/min "cloud platform charge" for self-hosted runners in private repos, announced for **2026-03-01**, was **postponed** pending re-evaluation. Public-repo runner usage stays free. [changelog 2025-12-16](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/)
- **Limits.** [limits](https://docs.github.com/en/actions/reference/limits), [cache eviction](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#usage-limits-and-eviction-policy)
  - Jobs: 6 h per job on hosted runners; a workflow run lasts at most 35 days; a matrix can have at most 256 jobs.
  - Queueing: at most 500 runs queued per 10 s.
  - Cache rate limits: 200 uploads/min and 1,500 downloads/min per repo.
  - Cache storage: 10 GB per repo by default. Entries not accessed in 7 days are evicted. User-owned repos can raise the limit to 10 TB, with overage billed.

### 1.6 `concurrency` and `workflow_dispatch`

- **concurrency.** At most one running and one pending job/run per group. A newly queued item cancels the existing *pending* one. `cancel-in-progress: true` also cancels the running one. `queue: max` allows up to 100 pending. `queue: max` combined with `cancel-in-progress: true` is a validation error. [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), [limits](https://docs.github.com/en/actions/reference/limits)
- **workflow_dispatch.** Input types are `boolean`, `choice`, `number`, `environment`, `string`. At most 25 top-level inputs and a 65,535-char payload. [syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
- **repository_dispatch.** `client_payload` allows at most 10 top-level properties and 65,535 chars; `event_type` is at most 100 chars. [events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)
- **REST.** `POST /repos/{o}/{r}/actions/workflows/{id}/dispatches` needs fine-grained Actions: write. `POST /repos/{o}/{r}/dispatches` needs Contents: write. [fine-grained permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)

---

## 2. Docker official GitHub Actions and multi-platform guidance

### 2.1 Current versions (`gh api repos/<repo>/releases/latest`, 2026-09-10)

| Action / workflow | Latest | Published | Docs examples use |
|---|---|---|---|
| docker/login-action | v4.6.0 | 2026-07-29 | `@v4` |
| docker/setup-qemu-action | v4.3.0 | 2026-09-01 | `@v4` |
| docker/setup-buildx-action | v4.3.0 | 2026-08-19 | `@v4` |
| docker/metadata-action | v6.2.0 | 2026-07-02 | `@v6` |
| docker/build-push-action | v7.3.0 | 2026-07-01 | `@v7` |
| docker/bake-action | v7.3.0 | 2026-07-01 | — |
| docker/setup-docker-action | — (not queried) | — | `@v5` |
| docker/github-builder (reusable workflows) | v1.17.0 | 2026-08-21 | `@v1` |
| docker/scout-action | v1.24.0 | 2026-07-30 | — |
| actions/attest | v4.2.2 | 2026-08-04 | — |
| actions/attest-build-provenance | v4.2.2 (wrapper over actions/attest since v4) | 2026-08-06 | — |
| sigstore/cosign-installer | v4.1.2 | 2026-05-07 | — |
| peter-evans/dockerhub-description | v5.0.0 | 2025-10-01 | Docker docs still pin v4.0.0 by SHA ([docs](https://docs.docker.com/build/ci/github-actions/update-dockerhub-desc/)) |
| aquasecurity/trivy-action | v0.36.0 | 2026-04-22 | — |
| anchore/scan-action | v7.4.2 | 2026-08-28 | — |

### 2.2 Multi-platform strategies

- **QEMU on one runner.** Docker's basic example chains `setup-qemu-action@v4`, `setup-buildx-action@v4` and `build-push-action@v7` with `platforms: linux/amd64,linux/arm64`, `push: true`. [Docker multi-platform GHA](https://docs.docker.com/build/ci/github-actions/multi-platform/)
  - Docker's general guidance: "Emulation with QEMU can be much slower than native builds"; use multiple native nodes or cross-compilation "if possible". [multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
- **Loading multi-platform images locally** (e.g. to test before push) isn't supported by the runner's default Docker setup. You need the containerd image store via `docker/setup-docker-action@v5` (`"containerd-snapshotter": true`) plus `load: true`. [Docker multi-platform GHA](https://docs.docker.com/build/ci/github-actions/multi-platform/)
  - Attestations are not added with `load: true` or the docker exporter. [attestations](https://docs.docker.com/build/ci/github-actions/attestations/)
- **Native runners: `docker/github-builder`.** Docker's page now says: to split platforms across runners "without maintaining a custom matrix and merge job, use the Docker GitHub Builder… compute the per-platform matrix, run each platform on its own runner, and create the final manifest for you." [Docker multi-platform GHA](https://docs.docker.com/build/ci/github-actions/multi-platform/)
  - `build.yml` (Dockerfile) and `bake.yml` (Bake). Called as `uses: docker/github-builder/.github/workflows/build.yml@v1` with job `permissions: contents: read, id-token: write`.
  - Default runner mapping: `default=ubuntu-24.04`, `linux/arm=ubuntu-24.04-arm`, `linux/arm64=ubuntu-24.04-arm`. Requires GitHub-hosted Linux runners. [architecture](https://docs.docker.com/build/ci/github-actions/github-builder/architecture/), [README](https://github.com/docker/github-builder)
  - Input defaults: `distribute: true`, `push: false`, `sign: auto` (signs attestation manifests when pushing), `sbom: false`, `cache: false`, `cache-mode: min`, `setup-qemu: false`, `set-meta-labels: false`.
  - Outputs include `digest`, `meta-json`, `signed`, `cosign-verify-commands`.
  - Credentials: secret `registry-auths` (YAML list, e.g. `registry: docker.io` + username/password), or keyless `registry-identities` with `type: dockerhub`, which needs a Docker Hub **organization** OIDC connection. [README](https://github.com/docker/github-builder)
- **Hand-written native matrix** (per-arch `push-by-digest` jobs + merge job running `docker buildx imagetools create`). The current Docker GitHub Actions multi-platform page no longer shows this example; it links to github-builder instead. The technique itself is not described as unsupported. (See Uncertainties.)

### 2.3 Cache backends

- **`type=gha`.** Docker calls it "the recommended cache to use inside your GitHub Actions workflows".
  - Not supported with the default `docker` driver; a docker-container builder (`setup-buildx-action`) is needed.
  - `scope` defaults to `buildkit`, so multiple images overwrite each other unless scoped. `mode` defaults to `min` (`max` is optional).
  - GitHub branch restrictions apply: only current, base and default branch caches are visible.
  - `build-push-action` auto-populates `url`/`token` and passes GITHUB_TOKEN as `ghtoken` to reduce cache-API throttling.
  - GitHub's 10 GB and 7-day eviction apply.
  - [gha backend](https://docs.docker.com/build/cache/backends/gha/), [GHA cache docs](https://docs.docker.com/build/ci/github-actions/cache/)
  - "As of April 15th, 2025, only GitHub Cache service API v2 is supported." [GHA cache docs](https://docs.docker.com/build/ci/github-actions/cache/)
- **`type=registry`.** Separate cache ref (e.g. `user/app:buildcache`), `mode=min|max`, `image-manifest=true` and `oci-mediatypes=true` by default. [registry backend](https://docs.docker.com/build/cache/backends/registry/) On Docker Hub the cache is a tag in the repo, so it's visible and counts as a tag (inference).
- **`type=inline`.** Supports only `min` mode. [GHA cache docs](https://docs.docker.com/build/ci/github-actions/cache/)

### 2.4 Provenance and SBOM attestations

- **build-push-action defaults.** Public GitHub repo → provenance `mode=max`; private → `mode=min`; none with the docker exporter or `load: true`. [attestations](https://docs.docker.com/build/ci/github-actions/attestations/)
  - Warning: for public repos the default provenance "contains the values of build arguments", so pass secrets via secret mounts. [SLSA provenance](https://docs.docker.com/build/metadata/attestations/slsa-provenance/)
- **SBOM** is not added by default (`sbom: true`). The generator is the BuildKit Syft scanner and it scans the final stage by default. [SBOM](https://docs.docker.com/build/metadata/attestations/sbom/)
- **Storage.** "Attestations are stored as manifest objects in the image index", one attestation manifest per platform manifest. With OCI artifact storage, `artifactType` is `application/vnd.docker.attestation.manifest.v1+json` with a `subject`. [attestation storage](https://docs.docker.com/build/metadata/attestations/attestation-storage/)
- **Docker Hub display.** Not described in the retrieved Docker Hub docs.
  - The Hub tag API for `n8nio/n8n:latest` lists only `linux/amd64` and `linux/arm64` under `images` (checked 2026-09-11). Whether that image carries attestations was not checked.
  - Docker OAT scopes mention reading "tags, image lists, attestations". [OAT](https://docs.docker.com/security/access-tokens/organization-access-tokens/)
  - Docker Scout uses an SBOM attestation if present, which also avoids its 10 GB image-analysis limit. [Scout analysis](https://docs.docker.com/scout/explore/analysis/)

### 2.5 docker/scout-action

- **Commands.** `quickview`, `compare`, `cves`, `recommendations`, `sbom`, `environment`. [scout-action](https://github.com/docker/scout-action)
- **Inputs.**
  - `exit-code` default `false` (return 2 when vulnerabilities or changes are detected); `exit-on` (compare only).
  - Filters: `only-severities`, `only-fixed`, `only-cisa-kev`.
  - `write-comment` default `true`, needs `pull-requests: write`.
  - `organization` is required for environments or compare-to-latest.
  - Docker Hub login via `dockerhub-user`/`dockerhub-password` or `login-action`.
- **Account requirements.** Sign in with a Docker ID. [Scout analysis](https://docs.docker.com/scout/explore/analysis/)
  - Scout-enabled repositories: Personal 1, Pro 2, Team unlimited. [pricing](https://www.docker.com/pricing/)
  - CLI `docker scout cves` does local analysis.
  - Docker Hub static vulnerability scanning (non-Scout) requires Pro/Team/Business. [Hub vulnerability scanning](https://docs.docker.com/docker-hub/repos/manage/vulnerability-scanning/)

### 2.6 GitHub artifact attestations (`actions/attest`, `attest-build-provenance`)

- **Availability.** Public repos on all current plans. Private or internal repos need **GitHub Enterprise Cloud**. Not supported on GHES. [actions/attest](https://github.com/actions/attest), [attest-build-provenance](https://github.com/actions/attest-build-provenance)
  - Public repos sign with Sigstore Public Good and write to a public transparency log. Private repos use GitHub's Sigstore instance, which has no transparency log. [artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- **Container images.** Pass `subject-name` (fully qualified, no tag) plus `subject-digest`. `push-to-registry: true` pushes the attestation to the registry. "When pushing to Docker Hub, please use 'docker.io' as the registry portion of the image name." [actions/attest](https://github.com/actions/attest)
  - Storage records are only created for **organization-owned** repos (`create-storage-record: false` disables them).
  - Permissions: `id-token: write`, `attestations: write`, `artifact-metadata: write`.
  - Verify with `gh attestation verify`. [use artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

### 2.7 cosign keyless signing with Docker Hub

- **Registry support.** Sigstore's registry-support page lists **Docker Hub** as tested. "Cosign signatures are stored using the OCI 1.1 referrer specification." [Sigstore registry support](https://docs.sigstore.dev/cosign/system_config/registry_support/)
- **Referrers API.** On 2026-09-11, `GET https://registry-1.docker.io/v2/n8nio/n8n/referrers/<index digest>` with an anonymous pull token returned `200` and an OCI index (empty `manifests`). Docker Hub serves the referrers API.
- **Keyless requirement.** Needs `id-token: write` (GitHub OIDC → Fulcio).
- **github-builder signing.** `docker/github-builder` signs attestation manifests keylessly by default when pushing (`sign: auto`) and emits `cosign verify` commands. Its examples push to `docker.io`. [README](https://github.com/docker/github-builder)
- **cosign-installer.** Current v4.1.2; pin a cosign version via `cosign-release` (example `v3.0.6`). [cosign-installer](https://github.com/sigstore/cosign-installer)

---

## 3. Docker Hub

### 3.1 Tokens and 2FA

- **Personal access tokens (PAT).** [PAT](https://docs.docker.com/security/access-tokens/personal-access-tokens/)
  - Created in Docker Home with a description, an expiration date and "**Access permissions:** Read, Write, or Delete".
  - "You can't edit the expiration date on an existing personal access token."
  - PATs are "Required when you have two-factor authentication turned on" (also with enforced SSO; password CLI sign-in isn't supported in those cases). [access tokens](https://docs.docker.com/security/access-tokens/)
  - Docker Desktop auto-generated tokens are capped at 5 per account. There is a fair-use clause on excessive token creation.
- **Hub API token scopes.** Valid scopes are `"repo:admin"`, `"repo:write"`, `"repo:read"`, `"repo:public_read"`; a higher scope implies the lower ones. `expires_at` is optional: "If omitted, the token will remain valid indefinitely". [Hub API spec](https://docs.docker.com/reference/api/hub/latest/)
  - Mapping UI names to scopes (Read→`repo:read`, Write→`repo:write`, Delete→`repo:admin`, public read-only→`repo:public_read`) is inference; see Uncertainties.
- **Repo overview/README updates.** `peter-evans/dockerhub-description` needs a "Personal Access Token with `read/write/delete` scope". For org repos the user needs Admin on the repo. Limits: README 25,000 bytes, short description 100 bytes. [dockerhub-description](https://github.com/peter-evans/dockerhub-description)
  - Implementation: `POST https://hub.docker.com/v2/auth/token`, then `PATCH https://hub.docker.com/v2/repositories/{repo}`. [source](https://github.com/peter-evans/dockerhub-description/blob/main/src/dockerhub-helper.ts)
- **Organization access tokens (OAT).** [OAT](https://docs.docker.com/security/access-tokens/organization-access-tokens/)
  - Plans: **Team (up to 10) or Business (up to 100)**; not available on Personal or Pro ([pricing](https://www.docker.com/pricing/)).
  - Granular scopes including `scope-image-push` (which implies pull), `scope-image-delete` and `scope-tag-read`; optional "Read public repositories".
  - Incompatible with Docker Desktop and Image Access Management. Legacy `/v2/repositories/{namespace}/...` API paths reject OATs. Separate rate limits.
- **OIDC connections** (announced 2026-07-31). [Docker blog](https://www.docker.com/blog/docker-oidc-connections-for-github-actions-available-for-docker-orgs/), [create/manage](https://docs.docker.com/security/authentication/oidc-connections/create-manage/)
  - Eligibility: orgs with Team, Business, DHI or DSOS.
  - Login: `docker/login-action` ≥ v4.5.0 with `DOCKERHUB_OIDC_CONNECTIONID`, `username` = org name, `id-token: write`.
  - "Only organization accounts can sign in using OIDC." Up to 5 rulesets per connection; tokens expire in minutes.

### 3.2 Repositories, visibility, retention

- **Auto-creation.** "Default repository privacy" is set per namespace. It is used to "automatically set privacy for repositories created via `docker push` commands when the repository doesn't exist yet" (Public or Private). [Hub settings](https://docs.docker.com/docker-hub/settings/#configure-default-repository-privacy)
  - The docs don't state the out-of-the-box value for personal namespaces.
  - "Disable public repos" exists for org namespaces only (2026-02-13). [release notes](https://docs.docker.com/docker-hub/release-notes/)
- **Plan limits.** Personal: unlimited public repos, **up to 1 private**, 200 pulls/6 h (docs). Pro/Team/Business: unlimited. [usage](https://docs.docker.com/docker-hub/usage/)
- **Naming.** Repo names are 2–255 chars of lowercase letters, digits, `-` and `_`, and can't be renamed. Short description is at most 100 chars. [create repo](https://docs.docker.com/docker-hub/repos/create/)
- **Retention.**
  - No image or tag inactivity-deletion policy found in current Docker Hub docs.
  - Docker (2025-02-21, updated 2025-04-08): "Storage Charges Delayed Indefinitely… we will provide a six-month notice". [Docker blog](https://www.docker.com/blog/revisiting-docker-hub-policies-prioritizing-developer-experience/)
  - Hub flags repos not updated in over a year with an icon. Archived repos are read-only (pushes blocked, pulls allowed). [archive](https://docs.docker.com/docker-hub/repos/archive/)
- **Other dated changes.** [release notes](https://docs.docker.com/docker-hub/release-notes/)
  - Docker Hub Automated Builds are deprecated; access ends **2027-04-01** (notice 2026-05-06).
  - Pushes and pulls may use `production.cloudfront.docker.com` since **2026-05-20** (egress allowlists, TLS trust).

### 3.3 Pull rate limits

- **Docs** (6-hour window): unauthenticated 100 per IPv4 address or IPv6 /64; Personal (authenticated) 200; Pro/Team/Business unlimited (fair use). [pulls](https://docs.docker.com/docker-hub/usage/pulls/)
- **What counts.** "A pull for a multi-arch image will count as one pull for each different architecture." "Version checks do not count towards usage pricing." [pulls](https://docs.docker.com/docker-hub/usage/pulls/)
  - Rate-limit headers "are returned on both GET and HEAD requests. Using GET emulates a real pull and counts towards the limit. Using HEAD won't."
- **Scope.** No namespace exemption is documented: "Unauthenticated and Docker Personal users using Docker Hub will experience rate limits on image pulls." Missing `ratelimit` headers can mean the image or IP is "unlimited in partnership with a publisher, provider, or an open source organization". [pulls](https://docs.docker.com/docker-hub/usage/pulls/)
- **Policy history.** "We did not enforce the Docker Hub rate limit changes previously scheduled for April 1, 2025… We will announce any future enforcement at least 6 months in advance." [Docker blog](https://www.docker.com/blog/revisiting-docker-hub-policies-prioritizing-developer-experience/)
- **Conflicting current signals.**
  - The pricing page lists Personal as "100 Docker Hub pulls/hr". [pricing](https://www.docker.com/pricing/)
  - Live anonymous HEAD on 2026-09-11 (`registry-1.docker.io/v2/n8nio/n8n/manifests/latest`): `ratelimit-limit: 100;w=3600`.
- **Abuse rate limit.** Per IP, "in the order of thousands of requests per minute", for all Hub properties including APIs. It returns a plain 429. [usage](https://docs.docker.com/docker-hub/usage/)
  - Shared-IP platforms may hit it even when authenticated. [pulls](https://docs.docker.com/docker-hub/usage/pulls/)

### 3.4 Immutable tags

- **Settings.** Repo Settings → General → Tag mutability: "All tags are mutable (Default)", "All tags are immutable" (including `latest`), or "Specific tags are immutable" via Go/RE2 regex. [immutable tags](https://docs.docker.com/docker-hub/repos/manage/hub-images/immutable-tags/)
- **Behavior.** You cannot push a new image to an existing immutable tag, and immutable tags can't be deleted. [immutable tags](https://docs.docker.com/docker-hub/repos/manage/hub-images/immutable-tags/), [tags](https://docs.docker.com/docker-hub/repos/manage/hub-images/tags/)
- **API.** `PATCH /v2/namespaces/{ns}/repositories/{repo}/immutabletags` and `POST …/immutabletags/verify` (admin only). The repository GET returns `immutable_tags_settings`. [Hub API spec](https://docs.docker.com/reference/api/hub/latest/)
- **Plan requirement.** Not stated in the docs.

### 3.5 Hub API / registry for "does tag X exist / what digest"

- **Hub API rate limit.** Per-minute limit with `X-RateLimit-Limit/Remaining/Reset`; on 429, `Retry-After`. Separate from pull limits. [Hub API spec](https://docs.docker.com/reference/api/hub/latest/)
- **Tag lookup.** `GET /v2/namespaces/{namespace}/repositories/{repository}/tags/{tag}` returns tag details; `HEAD` on the same path checks existence. `…/tags` lists tags.
  - The spec lists bearer auth for these routes. However, on 2026-09-11 an unauthenticated `GET https://hub.docker.com/v2/namespaces/n8nio/repositories/n8n/tags/latest` returned 200 with `x-ratelimit-limit: 180`.
  - Response fields include `digest` (index digest), `images[].digest` per architecture, `tag_last_pushed` and `last_updated`.
  - Repository `GET`/`HEAD` explicitly allow anonymous access for public repos.
- **Auth.** `POST /v2/auth/token` (username + PAT/OAT) is the current route; `POST /v2/users/login` is deprecated.
- **Repo description updates.** No repository update (PATCH) route was found in the retrieved spec. The dockerhub-description action uses the legacy `PATCH /v2/repositories/{repo}`, and OATs are rejected on legacy paths.
- **Registry route.** An anonymous token from `https://auth.docker.io/token?service=registry.docker.io&scope=repository:<ns>/<repo>:pull`, then `HEAD https://registry-1.docker.io/v2/<ns>/<repo>/manifests/<tag>` (with OCI index Accept header), returns `docker-content-digest`. HEAD doesn't count as a pull. [pulls](https://docs.docker.com/docker-hub/usage/pulls/)

---

## 4. Update-detection tooling

### 4.1 Renovate

- **Hosted options.** Mend Renovate Community Cloud is "a generous free tier… unlimited number of public and private repositories". [Mend overview](https://docs.renovatebot.com/mend-hosted/overview/)
  - The Community (OSS) plan gives more resources and Merge Confidence on request. Enterprise is paid.
  - Resources (Community): 1 concurrent job per org; active repos scheduled every 4 hours; 1 vCPU / 3 GB / 15 GB disk; 30-min job timeout.
  - Webhooks enqueue jobs on relevant repo changes. Onboarding/onboarded repos are scheduled daily. [job scheduling](https://docs.renovatebot.com/mend-hosted/job-scheduling/)
- **Install.** [installing](https://docs.renovatebot.com/getting-started/installing-onboarding/), [hosted apps config](https://docs.renovatebot.com/mend-hosted/hosted-apps-config/)
  - Install from https://github.com/apps/renovate, choosing "All repositories" or "Select repositories". Manage it at developer.mend.io.
  - "All repositories" leaves repos in silent mode (`dryRun=lookup`). "Selected repositories" always produces an onboarding PR.
  - The app adds `config:recommended` to onboarding config.
  - Community (free) users can't run arbitrary `postUpgradeTasks`. [Mend FAQ](https://docs.renovatebot.com/mend-hosted/faq/)
  - No github.com token is needed for GitHub-hosted repos. [github.com token](https://docs.renovatebot.com/mend-hosted/github-com-token/)
  - PRs and commits are made with the app's installation token. Per GitHub, App installation tokens trigger workflows normally, unlike GITHUB_TOKEN. [trigger a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- **Dockerfile manager.** Covers `FROM` (multi-stage, `--platform`, `AS`), `COPY --from`, `RUN --mount` and `# syntax`. "Renovate will automatically expand variables and `ARG` directives" (e.g. `ARG TAG=3.19.4` / `FROM alpine:${TAG}`). [dockerfile manager](https://docs.renovatebot.com/modules/manager/dockerfile/)
- **Docker versioning.** Suffixes like `-alpine` are treated as compatibility markers. Updates stay at the current precision: `1.1` goes to `1.2`, not to `1.2.0`. [docker versioning](https://docs.renovatebot.com/modules/versioning/docker/), [Renovate docker](https://docs.renovatebot.com/docker/)
- **Blocking majors.**
  - Preset `docker:disableMajor` = `packageRules: [{ enabled: false, matchDatasources: ['docker'], matchUpdateTypes: ['major'] }]`. [preset source](https://github.com/renovatebot/renovate/blob/main/lib/config/presets/internal/docker.preset.ts)
  - Or `packageRules[].allowedVersions` (e.g. `"<3"`). "`matchUpdateTypes` and `allowedVersions` cannot be used in the same package rule." [config options](https://docs.renovatebot.com/configuration-options/#packagerulesallowedversions)
- **Digests.** `pinDigests` / `docker:pinDigests` (included in `config:best-practices`) keeps the tag: `FROM node:14.15.1@sha256:…`. Re-pushes of the same tag produce digest-update PRs. [Renovate docker](https://docs.renovatebot.com/docker/), [pinDigests](https://docs.renovatebot.com/configuration-options/#pindigests)
  - Docker Hub release timestamps come from `tag_last_pushed`, and "digests may appear newer than they are". [docker datasource](https://docs.renovatebot.com/modules/datasource/docker/)
- **`github-releases` datasource.** `packageName: owner/repo`; release timestamps supported. [github-releases](https://docs.renovatebot.com/modules/datasource/github-releases/)
  - Draft releases are skipped; prereleases get `isStable=false`. [source](https://github.com/renovatebot/renovate/blob/main/lib/util/github/graphql/query-adapters/releases-query-adapter.ts)
  - `ignoreUnstable` (default on) skips unstable versions. [ignoreUnstable](https://docs.renovatebot.com/configuration-options/#ignoreunstable)
- **yt-dlp nightly facts** (`gh api repos/yt-dlp/yt-dlp-nightly-builds/releases`, 2026-09-10). [releases](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases)
  - Tags look like `2026.08.30.232658`, named "yt-dlp nightly …", **`prerelease: false`**.
  - Published around 23:15–23:31 UTC, not every day. The latest on 2026-09-10 was `2026.08.30.232658`.
  - 23 assets, including `yt-dlp_linux`, `yt-dlp_linux_aarch64`, `yt-dlp_musllinux(_aarch64)`, `yt-dlp` (zipimport), `SHA2-256SUMS` and `SHA2-256SUMS.sig`.
- **Versioning such tags.**
  - Regex custom managers default to `semver-coerced` ("v1"→"1.0.0", "2.1"→"2.1.0"). How it treats a 4-component date-time tag isn't documented; it likely ignores the 4th part (inference). [semver-coerced](https://docs.renovatebot.com/modules/versioning/semver-coerced/)
  - `loose` "does its best to sort versions". [loose](https://docs.renovatebot.com/modules/versioning/loose/)
  - `regex:` versioning accepts numeric `major`/`minor`/`patch`/`build`/`revision` groups, with `build` handled like patch. [regex versioning](https://docs.renovatebot.com/modules/versioning/regex/)
- **Custom regex managers.** Required: `managerFilePatterns`, `matchStrings` with `currentValue` (or `currentDigest`), `depName`/`packageName`, and a datasource (capture or template). [regex manager](https://docs.renovatebot.com/modules/manager/regex/)
  - The documented example matches `# renovate: datasource=… depName=… packageName=… versioning=…` comments above `(?:ENV|ARG) .+?_VERSION=` lines.
  - RE2 syntax (no lookahead or backreferences); matching is per file, not per line. `extractVersion` strips prefixes.
- **Automerge.** [automergeType](https://docs.renovatebot.com/configuration-options/#automergetype), [automerge](https://docs.renovatebot.com/key-concepts/automerge/)
  - `automergeType`: `pr` (default), `branch`, `pr-comment`.
  - `branch`: create the branch, wait for tests, push directly to the base branch if up to date and green. A PR is raised only if tests fail or stay pending more than 25 h (`prNotPendingHours`). Merge queues require Renovate on the bypass list.
  - Status checks must pass unless `ignoreTests: true`. Renovate automerges one branch per target per run and needs a gap where the branch is green and up to date.
  - `platformAutomerge` (default true) uses GitHub auto-merge. Docs warn to enable "Require status checks before merging", or GitHub may merge before tests finish. [platformAutomerge](https://docs.renovatebot.com/configuration-options/#platformautomerge)
- **Schedules.** "Setting a `schedule` does not itself cause or trigger Renovate to run." [schedule](https://docs.renovatebot.com/configuration-options/#schedule), [scheduling](https://docs.renovatebot.com/key-concepts/scheduling/)
  - Cron only with `*` in the minutes field; default "at any time"; UTC unless `timezone` is set.
  - Allow windows of at least 3–4 h. For the Mend app, "Mend decides when Renovate runs".
  - `minimumReleaseAge` needs release timestamps and adds a `renovate/stability-days` check. [minimumReleaseAge](https://docs.renovatebot.com/configuration-options/#minimumreleaseage)

### 4.2 Dependabot

- **`docker` ecosystem.** Version updates supported; security updates **not** supported. Covers Dockerfiles, Kubernetes manifests and Helm charts; `docker-compose` is a separate ecosystem. [ecosystems](https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories)
- **Blocking majors.** `ignore` / `allow` accept `update-types: ["version-update:semver-major" | "…-minor" | "…-patch"]`. [options](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
- **Schedule.** `schedule.interval` is daily, weekly, monthly, quarterly, semiannually, yearly, or `cron` (with `cronjob`). [options](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
  - **Default 3-day cooldown** for version updates, configurable via `cooldown` (`default-days`, `semver-major-days`, …).
- **ARG in `FROM`.** Not supported. dependabot-core [#2057](https://github.com/dependabot/dependabot-core/issues/2057) ("Add global ARG support for Dockerfiles") is open. [#4597](https://github.com/dependabot/dependabot-core/issues/4597) and [#10190](https://github.com/dependabot/dependabot-core/issues/10190) were closed as not planned (2022-09-15, 2026-07-20).
- **Arbitrary GitHub release binaries** (e.g. yt-dlp nightly): no matching ecosystem. `github-actions` only updates `uses:` references; `pre-commit` covers pre-commit hooks. [ecosystems](https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories)

### 4.3 Self-written scheduled workflow

- **GitHub REST.** [REST limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [conditional requests](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests)
  - Limits: GITHUB_TOKEN 1,000 req/h per repo; unauthenticated 60/h; PAT 5,000/h.
  - Secondary limits: 100 concurrent requests, 900 points/min, and content-creating requests about 80/min or 500/h.
  - "Making a conditional request does not count against your primary rate limit if a `304` response is returned" (authorized request with `if-none-match`).
- **Latest release endpoint.** `GET /repos/{owner}/{repo}/releases/latest` returns "the most recent non-prerelease, non-draft release, sorted by the `created_at` attribute". `created_at` "is the date of the commit used for the release, and not the date when the release was drafted or published." [releases](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
- **Docker Hub.** Hub API is per-minute limited (observed 180/min anonymous); registry manifest **HEAD** does not count toward pull limits (3.3/3.5). The abuse limit applies per IP.
- **Platform constraints to design around** (facts from §1):
  - Cron delays or drops.
  - The 60-day auto-disable (public repos).
  - GITHUB_TOKEN pushes don't trigger `push` workflows, but `workflow_dispatch` does.
  - GITHUB_TOKEN PRs need manual approval to run CI.
  - GITHUB_TOKEN can't edit workflow files.
  - Committing "last seen" state needs `contents: write`.

---

## 5. Supply-chain hardening

- **GitHub "Secure use reference".** [secure use](https://docs.github.com/en/actions/reference/security/secure-use)
  - "Pinning an action to a full-length commit SHA is currently the only way to use an action as an immutable release"; tags "can be moved or deleted".
  - Set the default GITHUB_TOKEN to read and raise permissions per job.
  - Secrets: don't use JSON/YAML blobs as secrets; mask with `::add-mask::`; register derived values as secrets; rotate.
  - Pass untrusted input through env vars, not `${{ }}` in `run:`.
  - Avoid `pull_request_target`/`workflow_run` with untrusted checkouts. Use OpenSSF Scorecards.
  - Dependabot alerts "will not create alerts for actions pinned to SHA values" (semver-tagged only).
- **Policies.** SHA-pinning requirement and action blocklists since 2025-08-15. [changelog](https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/)
  - Immutable releases GA on 2025-10-28: tags and assets locked, with release attestations. [changelog](https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/)
- **GitHub Actions 2026 security roadmap** (published 2026-03-26, updated 03-30). [GitHub blog](https://github.blog/news-insights/product-news/whats-coming-to-our-github-actions-2026-security-roadmap/)
  - Workflow `dependencies:` lock with SHAs, like go.mod/go.sum (preview in 3–6 months, GA around 6).
  - Policy-driven execution controls (shipped as public preview 2026-06-18).
  - Scoped secrets.
  - Actions data stream.
  - Native egress firewall for hosted runners (preview in 6–9 months).
  - Cited incidents: tj-actions/changed-files, Nx, trivy-action.

| Incident | Advisory | Dates | Mechanism / notes |
|---|---|---|---|
| tj-actions/changed-files | [GHSA-mrrh-fwg8-r2c3](https://github.com/advisories/GHSA-mrrh-fwg8-r2c3), CVE-2025-30066 | published 2025-03-15 | ≤45.0.7 compromised, secrets exposed in logs; patched 46.0.1 |
| reviewdog/action-setup (+ others) | [GHSA-qmg3-hpqr-gqvc](https://github.com/advisories/GHSA-qmg3-hpqr-gqvc), CVE-2025-30154 | published 2025-03-19 | `v1` compromised during a window |
| trivy-action script injection | [GHSA-9p44-j4g5-cfx5](https://github.com/advisories/GHSA-9p44-j4g5-cfx5), CVE-2026-26189 | 2026-02-18 | 0.31.0–0.33.1 unsafe env file sourcing; fixed 0.34.0 |
| xygeni/xygeni-action | [GHSA-f8q5-h5qh-33mh](https://github.com/advisories/GHSA-f8q5-h5qh-33mh), CVE-2026-31976 | ~2026-03-03→10; published 2026-03-11 | Compromised App credentials moved `v5` tag to an unmerged-PR commit (C2 implant) |
| **Trivy ecosystem** (trivy, trivy-action, setup-trivy, Docker Hub images) | [GHSA-69fq-xp46-6x23](https://github.com/advisories/GHSA-69fq-xp46-6x23), CVE-2026-33634; [vendor advisory](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23) | 2026-03-19 (tags/binary), 2026-03-22 (Docker Hub v0.69.5/0.69.6); published 2026-03-24 | Continuation of a late-Feb 2026 attack after non-atomic credential rotation. 76/77 trivy-action tags force-pushed to an infostealer that dumped `Runner.Worker` memory (~12 h); all 7 setup-trivy tags (~4 h); malicious trivy v0.69.4 on GHCR/ECR/Docker Hub. **Not affected:** trivy-action `0.35.0` (immutable release), SHA pins to commits after 2025-04-09, images referenced by digest. |
| step-security/harden-runner (Community tier) | [GHSA-cpmj-h4f6-r6pq](https://github.com/advisories/GHSA-cpmj-h4f6-r6pq), [GHSA-g699-3x6g-wm3g](https://github.com/advisories/GHSA-g699-3x6g-wm3g), [GHSA-46g3-37rh-v698](https://github.com/advisories/GHSA-46g3-37rh-v698) | 2026-02-09, 2026-03-17 | Egress-policy / logging bypasses |
| Other 2026 Actions advisories (injection class) | e.g. [GHSA-8q5r-mmjf-575q](https://github.com/advisories/GHSA-8q5r-mmjf-575q) (claude-code-action), [GHSA-wpqr-6v78-jr5g](https://github.com/advisories/GHSA-wpqr-6v78-jr5g) (run-gemini-cli), [GHSA-r79c-pqj3-577x](https://github.com/advisories/GHSA-r79c-pqj3-577x) (super-linter) | 2026-02 → 2026-06 | From `gh api /advisories?ecosystem=actions` |

- **Vulnerability-scanning actions.**
  - `aquasecurity/trivy-action` v0.36.0 (2026-04-22). README examples use `exit-code: '1'`, `ignore-unfixed: true`, `severity: CRITICAL,HIGH`. Built-in DB caching is on by default "to avoid rate limiting issues". [trivy-action](https://github.com/aquasecurity/trivy-action)
  - `anchore/scan-action` (Grype) v7.4.2 (2026-08-28). `fail-build` fails on severity ≥ `medium` by default; `severity-cutoff` is adjustable; `fail-build: false` is report-only. Output formats: SARIF, JSON, CycloneDX, table. [scan-action](https://github.com/anchore/scan-action)
  - `docker/scout-action` v1.24.0. `exit-code` defaults to `false` (report-only); `exit-on` gates `compare`. [scout-action](https://github.com/docker/scout-action)
  - Report-only vs gating: GitHub's secure-use reference does not prescribe it. The tools' own defaults differ (Grype gates, Scout reports, Trivy examples gate).

---

## Trade-off notes

### Public vs private repo (GitHub Free / Docker Personal)

| Aspect | Public repo (current) | Private repo |
|---|---|---|
| Hosted runner cost | Free (standard runners) | 2,000 included min/month, then $0.006/min x64, $0.005/min arm64 |
| Standard runner size (x64 and arm64) | 4 vCPU / 16 GB | 2 vCPU / 8 GB |
| 60-day scheduled-workflow auto-disable | Applies | Not documented |
| GitHub artifact attestations | Available; Sigstore public-good + public transparency log | Requires GitHub Enterprise Cloud |
| build-push-action default provenance | `mode=max` (build-arg values visible) | `mode=min` |
| Fork PR workflow approval | First-time contributors need approval by default | N/A |
| Docker Hub side | Unlimited public image repos | Only 1 private repo on Personal |

### Multi-arch build strategies on GitHub-hosted runners

| Strategy | Runners | Build speed | Workflow complexity | Notes |
|---|---|---|---|---|
| QEMU emulation, single `build-push-action` job | 1× `ubuntu-latest` | arm64 half emulated: "can be much slower than native" | Lowest | Docker's canonical example; `load: true` needs the containerd store; one job pushes the manifest list directly |
| Hand-written native matrix (`push-by-digest`) + merge job (`buildx imagetools create`) | `ubuntu-24.04` + `ubuntu-24.04-arm` + merge job | Native | Highest: digest artifacts, merge job, tag and attestation handling | No longer shown on Docker's GHA multi-platform page |
| `docker/github-builder` `build.yml@v1` (reusable workflow) | Per-platform jobs on `ubuntu-24.04` / `ubuntu-24.04-arm`, plus finalize | Native | Low (one `uses:` + inputs) | Docker-maintained; signs attestation manifests by default on push; `registry-auths` secret for PAT (OIDC is org-only); GitHub-hosted Linux runners only; tag references allowed even under the SHA-pin policy for reusable workflows; test-before-push hook not documented in retrieved docs |

### Docker Hub credential options for a personal namespace

| Mechanism | Personal namespace? | Can push | Can update repo description (legacy PATCH) | Notes |
|---|---|---|---|---|
| PAT "Read" (`repo:read`) | Yes | No | No | Pull, including private repos |
| PAT "Write" (`repo:write`) | Yes | Yes | Not per dockerhub-description docs | Minimum for push |
| PAT "Delete" (`repo:admin`) | Yes | Yes | Yes (dockerhub-description requires read/write/delete) | Broadest; can delete |
| PAT public read-only (`repo:public_read`) | Yes (API scope) | No | No | Pull auth for rate-limit attribution |
| Organization access token | No (Team/Business org) | Yes (`scope-image-push`) | No (legacy paths reject OATs) | Namespace would have to be an org |
| OIDC connection | No (org accounts only; Team/Business/DHI/DSOS) | Yes (ruleset-scoped) | Not documented | No stored secret; login-action ≥4.5.0 |

### Update-detection options

| Option | n8n base image | yt-dlp nightly (GitHub release) | Cadence | Cost / infra | Identity & CI triggering | Notable limits |
|---|---|---|---|---|---|---|
| Mend Renovate app (Community Cloud) | `dockerfile` manager (incl. ARG-expanded `FROM`), `docker:disableMajor` or `allowedVersions`, `pinDigests` | `customManagers` regex + `github-releases`; versioning must be configured for 4-part tags | ~4-hourly for active repos, plus webhooks; `schedule` only restricts | Free; no workflow to maintain | Renovate App token: PR/push CI runs normally; branch automerge can push to `main` (no rulesets here) | 1 concurrent job, 30-min timeout, no arbitrary `postUpgradeTasks` |
| Dependabot | `FROM` tag updates, ignore `semver-major`; **no ARG-in-FROM** | Not supported | daily…yearly or cron; default 3-day cooldown | Free, built in | Dependabot identity | Docker security updates unsupported |
| Self-written scheduled workflow | Hub tag API or registry HEAD (digest) | `releases/latest` REST | cron ≥5 min, best effort (delays/drops) | Free Actions minutes (public) | GITHUB_TOKEN: no `push`-triggered runs, PR runs need approval, can't touch workflow files; dispatch works | 60-day auto-disable (public); GITHUB_TOKEN 1,000 req/h; Hub API per-minute limit |

---

## Conflicts / uncertainties

1. **Docker Hub pull limits.**
   - Docs: 100/6 h unauthenticated and 200/6 h Personal ([pulls](https://docs.docker.com/docker-hub/usage/pulls/), [usage](https://docs.docker.com/docker-hub/usage/)).
   - Pricing page: Personal "100 Docker Hub pulls/hr" ([pricing](https://www.docker.com/pricing/)).
   - Live anonymous HEAD from one IP on 2026-09-11: `ratelimit-limit: 100;w=3600` (100/hour).
   - Docker's 2025 blog promised 6 months' notice for enforcement changes; no newer announcement was found. GitHub-hosted runner IPs may be treated differently; that wasn't tested.
2. **60-day rule "activity" is undefined.** Unknown whether bot/GITHUB_TOKEN commits, workflow runs, or API re-enables reset it. The docs don't mention private repos at all.
3. **SSH pushes vs the `workflow` scope.** No GitHub documentation found. The scope is documented for OAuth/PAT tokens and the "Workflows" permission for fine-grained PATs and GitHub Apps. Community reports and error strings only concern token-based pushes. Not tested, since no pushes were allowed.
4. **Mend scheduling.** The overview and job-scheduling tables say "Every 4 hours" for active repos on Community Cloud. The Renovate Status table in the same job-scheduling page lists new/activated repos as "Hourly" ([job scheduling](https://docs.renovatebot.com/mend-hosted/job-scheduling/)).
5. **Hub API auth for the tag endpoint.** The spec lists `bearerAuth` only, but anonymous `GET …/tags/{tag}` on a public repo returned 200 (2026-09-11). This may not be a stable contract.
6. **PAT naming.** The docs UI says "Read, Write, or Delete". The API says `repo:read|write|admin|public_read`. The one-to-one mapping (Delete→`repo:admin`) and whether the UI still offers a "public repo read-only" option are inferred, not documented on the retrieved pages. The docs don't list preset expiration choices.
7. **Default repository privacy** for a personal namespace (applied on push auto-creation): configurable, but the out-of-the-box value is not stated.
8. **Immutable tags plan requirement:** not stated. Pricing page line items for it weren't found.
9. **Docker Hub UI display of attestation manifests** isn't documented on the retrieved pages. The Hub tag API sample showed only OS/arch images.
10. **Manual `push-by-digest` + `imagetools create` pattern** has been dropped from Docker's GitHub Actions multi-platform page in favor of github-builder. No current Docker doc was found that deprecates the technique; buildx `imagetools` itself was not re-verified.
11. **GitHub billing multipliers.** The current billing page lists per-SKU per-minute prices. The retrieved text didn't show whether included private-repo minutes are consumed 1:1 per SKU or with multipliers (old model: Linux 1×, Windows 2×, macOS 10×).
12. **Renovate `semver-coerced` with 4-part tags** (`2026.08.30.232658`): behavior inferred (likely drops the 4th component, so same-day builds may compare equal), not documented. Leading zeros (`08`) vs strict parsing also not verified.
13. **Dependabot Docker digest-pinning behavior** wasn't checked in the retrieved docs.
14. **ubuntu-26.04 / ubuntu-26.04-arm** are marked "Public preview". `ubuntu-latest` "might not be the most recent version of the operating system available" ([runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)).
