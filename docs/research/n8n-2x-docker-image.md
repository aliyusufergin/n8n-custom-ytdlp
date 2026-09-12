# n8n 2.x official Docker image: facts for an image extender

Retrieved: 2026-09-10

Release/tag facts re-verified 2026-09-11 ~13:25 UTC. The image was inspected in depth on `n8nio/n8n:2.38.6` (tag commit `0e7a133`) and spot-checked on `2.38.7` (tag commit `a2d0f76`). Between those two tags no file under `docker/`, `packages/@n8n/config/`, the task-runner code or the release/docker workflows changed (`gh api repos/n8n-io/n8n/compare/n8n@2.38.6...n8n@2.38.7`: 6 commits, 27 files). Empirical checks ran on a linux/amd64 host, Docker 29.8.0.

Source links point at tag `n8n@2.38.6` unless noted. Docs pages are also available as raw markdown by appending `.md`.

---

## Key findings

- **Current versions (2026-09-11).**
  - Newest stable 2.x is **2.38.7**: GitHub `releases/latest`, npm `stable`/`latest`, and Docker Hub `stable`/`latest` = `sha256:a8c95f75c6fd…`.
  - Newest beta is **2.39.4**: GitHub prerelease, npm `beta`/`next`/`rc`, Docker `beta`/`next`.
  - One day earlier: stable 2.38.6, beta 2.39.2.
  - Sources: [releases/latest API](https://api.github.com/repos/n8n-io/n8n/releases/latest), [npm dist-tags](https://registry.npmjs.org/-/package/n8n/dist-tags), [Docker Hub tag API](https://hub.docker.com/v2/repositories/n8nio/n8n/tags/stable).
- **3.x.** There is no 3.x release, npm version or `n8n@3*` git tag.
  - A long-lived `3.x` branch exists, and Docker publishes `v3-nightly*` (daily) and `v3-rc*` (Mondays) images from it.
  - Docs say 3.0 is "scheduled for October 2026".
  - The current release pipeline rejects major bumps, so how `stable`/`latest` will move to 3.x is not yet defined.
  - Sources: [v3.0 breaking changes](https://docs.n8n.io/changelog/v30-breaking-changes), [build-v3-nightly.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/build-v3-nightly.yml), [determine-version-info.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/determine-version-info.mjs).
- **Channel model.** A new minor ships weekly (Tuesdays) into `beta`. At that moment the previous beta minor line is promoted to `stable`.
  - Patches keep shipping on both lines and on 1.123.x (`v1` track), so the most recently published version is often not the highest semver.
  - The GitHub `prerelease` flag is flipped when a version is promoted, and it has anomalies (e.g. `n8n@2.38.1` is `prerelease=false`). "Max semver of non-prerelease releases" is therefore **not** a safe signal.
  - Sources: [release-publish-post-release.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-publish-post-release.yml), [promote-github-release.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/promote-github-release.mjs).
- **Best "newest stable" signal:** `GET https://api.github.com/repos/n8n-io/n8n/releases/latest` → `tag_name` `n8n@X.Y.Z`.
  - n8n's own installer uses it ([get-n8n.sh](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/get-n8n.sh)). Cross-check with npm dist-tag `stable`.
  - The exact Docker version tag is pushed *before* the GitHub release is created: in [release-publish.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-publish.yml), `create-github-release` needs `publish-to-docker-hub`.
  - Filter to `^n8n@2\.` so a future 3.x promotion doesn't silently switch majors.
- **Docker tag families** ([docker-tags.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/docker/docker-tags.mjs), [docker-build-push.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/docker-build-push.yml)):
  - Consume the plain `X.Y.Z` tag. It is an OCI image index with linux/amd64 and linux/arm64.
  - `X.Y.Z-amd64` and `X.Y.Z-arm64` are single-platform build intermediates.
  - `X.Y.Z-<sha7>` tags are the per-commit immutable refs.
  - There are **no floating major/minor tags** (`2`, `2.38` return 404). `1` is stale (1.123.27, pushed 2026-03-25).
  - **Version tags can be re-pushed:** `2.38.0` got a new digest on 2026-09-08, a week after release. Track digests, not only version strings.
- **`-pc` tags** are a V8 **pointer-compressed** Node build, "internal to n8n Cloud, no support or stability guarantees". Use the plain tags ([README](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/README.md), [docker-bake.hcl](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/docker-bake.hcl), [node-pc Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/node-pc/Dockerfile)).
- **Image construction.**
  - Build chain: Docker Hardened Image `dhi.io/node:26.7.0-alpine3.24-dev` → `n8nio/base:26.7.0` → `n8nio/n8n`.
  - Runtime: Node **26.7.0**, musl, busybox `/bin/sh`. **apk-tools is removed.** No bash, curl, python3 or openssl CLI.
  - `USER node` (1000:1000), `WORKDIR /home/node`, `ENTRYPOINT ["tini","--","/docker-entrypoint.sh"]`, `EXPOSE 5678/tcp`.
  - No CMD, VOLUME or HEALTHCHECK.
  - Sources: [n8n Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/Dockerfile), [n8n-base Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n-base/Dockerfile).
- **Attestations.** SLSA provenance, CycloneDX SBOM and OpenVEX are attached via cosign **on GHCR only** (`ghcr.io/n8n-io/n8n`, same index digest as Docker Hub). No in-index BuildKit attestations exist for 2.38.x, and no cosign `.sig` was found ([docker-build-push.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/docker-build-push.yml)).
- **Data dir.** Persist `/home/node/.n8n` as a volume. It holds the auto-generated encryption key in `config` (mode 0600), the SQLite DB, and filesystem binary data under `storage/`. Set `N8N_ENCRYPTION_KEY` explicitly for multi-container/queue setups ([Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker), [custom encryption key](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key), [binary-data.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/core/src/binary-data/binary-data.config.ts)).
- **Health endpoints.** `/healthz` means the process is up. `/healthz/readiness` returns 200 only when the DB is connected, migrated and the server is ready (503 before). Busybox `wget` exists in the image; `curl` does not ([Monitor n8n](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/monitor-n8n), [abstract-server.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/cli/src/abstract-server.ts)).
- **Execute Command is excluded by default.**
  - `NODES_EXCLUDE` defaults to `["n8n-nodes-base.executeCommand","n8n-nodes-base.localFileTrigger"]`.
  - Re-enable with `NODES_EXCLUDE=["n8n-nodes-base.localFileTrigger"]` (keeps the file trigger blocked) or `NODES_EXCLUDE=[]`.
  - Sources: [nodes.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/nodes.config.ts), [v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes).
- **Where Execute Command runs.** It calls `spawn(command,{cwd: process.cwd(), shell: true})` **inside the n8n process** (the main instance, or queue-mode workers for production executions). It does not run in task runners.
  - Verified: it runs as `uid=1000(node)`, cwd `/home/node`, `/bin/sh` → busybox.
  - So yt-dlp/ffmpeg must be in the image used for main **and** workers, not in `n8nio/runners`.
  - Sources: [ExecuteCommand.node.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/nodes-base/nodes/ExecuteCommand/ExecuteCommand.node.ts), [Execute Command docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand).
- **Code node.** Task runners are on by default, and `N8N_RUNNERS_MODE` defaults to `internal` (a child process in the same container).
  - `require('child_process')` is rejected ("Module 'child_process' is disallowed") unless `NODE_FUNCTION_ALLOW_BUILTIN` allows it.
  - In external mode the binaries would have to be in the runners image.
  - Sources: [runners.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/runners.config.ts), [js-runner-config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/task-runner/src/config/js-runner-config.ts), [Set up task runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners).
- **File nodes.** Read/Write Files from Disk (and Read Binary Files) may only touch `N8N_RESTRICT_FILE_ACCESS_TO`, default `~/.n8n-files` = `/home/node/.n8n-files`.
  - That directory **does not exist in the image**.
  - `N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES=true` also blocks `~/.n8n`.
  - Verified: reading `/tmp/...` fails with "Access to the file is not allowed."
  - Source: [security.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/security.config.ts).
- **Extending the image.** The only official recipe is on the [Execute Command docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand): `FROM n8nio/n8n` → `USER root` → restore apk by copying `/sbin/apk`, `/lib/apk` and `/usr/lib/libapk*` from `alpine:3.22` → `apk add` → `USER node`.
  - **That recipe fails on 2.38.7** (exit 15). Copying `/lib/apk` replaces the image's checksum-pinned DHI apk database.
  - A non-official variant worked: copy only `/sbin/apk` and `/usr/lib/libapk*` from `alpine:3.24`, keep the image's database, then `apk add --no-cache ffmpeg`. Empirical check E9.

---

## 1. Release channels & versions

### 1.1 State on 2026-09-11 (re-verified)

| Line | GitHub Releases | git pointer tag | npm dist-tags | Docker Hub `n8nio/n8n` |
|---|---|---|---|---|
| stable | `n8n@2.38.7`, `prerelease=false`, returned by `/releases/latest`, published 2026-09-11T08:06:20Z | `stable` → `n8n@2.38.7` (a2d0f76) | `stable`=`latest`=2.38.7 | `2.38.7` pushed 07:58:12Z; `stable`/`latest` retagged 08:14:12Z → `sha256:a8c95f75c6fdf65f5f2b7a7b354744eaa1c62bb911b5c00af6499c3f38e4cd32` |
| beta | `n8n@2.39.4`, `prerelease=true`, 2026-09-11T08:29:50Z | `beta` → `n8n@2.39.4` | `beta`=`next`=`rc`=2.39.4 | `2.39.4` pushed 08:23:18Z; `beta`/`next` → `sha256:5fa13ec66b57…` |
| 1.x maintenance | `n8n@1.123.79`, `prerelease=false`, 2026-09-10T06:26:27Z | `v1` → `n8n@1.123.79` (28dd85a) | none | `1.123.79`; floating `1` is stale → 1.123.27 (pushed 2026-03-25T13:23Z) |
| 3.x | none | branch `3.x` (head a496f5a, 2026-09-11T12:44Z); 0 tags matching `n8n@3` | none (npm majors present: 0, 1, 2) | `v3-nightly`, `v3-nightly-<YYYYMMDD>`, `v3-nightly-<sha7>` (daily), `v3-rc` (last 2026-09-07); label `org.opencontainers.image.version=v3-nightly`, `N8N_RELEASE_TYPE=nightly` |

### 1.2 How stable vs beta is designated (source of truth: release scripts)

**Tracks.**
- The tracks are `stable`, `beta` and `v1` (`RELEASE_TRACKS` in [github-helpers.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/github-helpers.mjs)).
- Each track is a force-moved git tag pointing at a release commit ([move-track-tag.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/move-track-tag.mjs), [release-update-pointer-tag.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-update-pointer-tag.yml)).

**Track assignment** ([determine-version-info.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/determine-version-info.mjs)):
- A version whose `major.minor` equals a track pointer's version inherits that track (patch release).
- Otherwise it must be exactly the next minor after the current beta. It becomes `beta`, and `new_stable_version` = the previous beta version.
- A major bump throws `'Major version bumps are not allowed by this pipeline'`.
- `release_type` is `rc` for `-rc.`/`-exp` versions, else `stable`.
  - So beta images also carry `ENV N8N_RELEASE_TYPE=stable` (verified on `2.39.4`).
  - Nightly builds carry `nightly`.

**GitHub Releases** ([release-create-github-releases.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-create-github-releases.yml), [create-github-release.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/create-github-release.mjs)):
- Each release is named after its tag `n8n@X.Y.Z`.
- `prerelease = (track == 'beta' || experimental)` and `make_latest = (track == 'stable' && !experimental)`.
- The same body is **also** published as a release on the track tag (`stable` or `beta`). The old track release is deleted first, and the track release is created with `make_latest=false`.
  - This is why GitHub shows releases literally named `stable` (non-prerelease) and `beta` (prerelease). They are moving duplicates, not versions.
- On promotion, [promote-github-release.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/promote-github-release.mjs) updates the promoted `n8n@X.Y.Z` release to `prerelease:false, make_latest:'true'` and recreates the `stable` release.
- `v1` releases get `prerelease=false, make_latest=false`, so 1.x never becomes `releases/latest`.

**npm / Docker Hub / GHCR** ([release-push-to-channel.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-push-to-channel.yml)):
- Channel `beta`:
  - `npm dist-tag add n8n@V next` and `… beta`.
  - `docker buildx imagetools create -t n8nio/n8n:beta n8nio/n8n:V`, and the same for `:next`, `n8nio/runners:beta|next`, `ghcr.io/n8n-io/n8n|runners:beta|next`.
- Channel `stable`: the same, with `latest` and `stable`.
- Floating tags are therefore pure retags with the identical digest.
- The npm `rc` dist-tag is a side effect: `n8n` is first published with `--tag rc` ([release-publish.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-publish.yml)), so `rc` = the most recent publish.

**Post-release** ([release-publish-post-release.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-publish-post-release.yml)):
- The version is pushed to its own track's channel.
- On a minor bump, the jobs `promote-previous-beta-to-stable` and `promote-previous-minor-github-release-to-latest` run for `new_stable_version`.

**Docs.**
- [v2.0 breaking changes, Release channels](https://docs.n8n.io/changelog/v20-breaking-changes): channels were renamed `latest`→`stable` and `next`→`beta`. The old tags are still published "for now" and "will be removed in a future major version". Recommendation: "Pin your n8n version to a specific version number".
- [Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker): "n8n releases a new minor version most weeks. The `stable` version is for production use. `beta` is the most recent release. The `beta` version may be unstable."

### 1.3 Explaining the observed anomalies

- **`n8n@2.37.7…2.37.11` shipped after `2.38.0`.** For example, npm 2.38.0 is 2026-09-01T07:17Z and 2.37.11 is 2026-09-07T07:55Z. During 2026-09-01…09-07, 2.37.x was the `stable` line and 2.38.x the `beta` line.
- **2.39.0 (2026-09-08T08:24Z) moved things along.** 2.38.x was promoted to stable (beta pointer 2.38.4 at that time), and 2.37.x stopped.
- **`n8n@2.38.3` is `prerelease=true` while `n8n@2.38.4` is `false`.** 2.38.0–2.38.4 were all created as beta-track prereleases. 2.38.4 was flipped to non-prerelease/latest by the promotion; its `published_at` still reads 2026-09-07T08:01:50Z. 2.38.5–2.38.7 were created directly on the stable track.
- **`n8n@2.38.1` is `prerelease=false`.** This is not explained by the logic above (see Conflicts).
- **`n8n@1.123.79` still ships** on the `v1` track: git tag `v1` → the commit of `n8n@1.123.79`.
- **`published_at` is not a reliable ordering key.** `n8n@2.38.0` shows 2026-09-08T07:39:53Z because it was re-released (§1.8).

### 1.4 "Highest semver" ≠ "most recently published" (npm `time`)

- 2.36.9 was published 2026-08-31T07:51Z, after 2.37.0 (2026-08-25).
- 2.37.11 was published 2026-09-07, after 2.38.0 (2026-09-01).
- 1.123.79 was published 2026-09-10T06:16Z, after 2.39.1.
- GitHub order on 2026-09-11: `n8n@2.39.3` 07:45Z → `n8n@2.38.7` 08:06Z → `n8n@2.39.4` 08:29Z.

### 1.5 Machine-queryable signals (exact calls, real trimmed output)

1. **GitHub latest release.** This is the recommended primary signal and what n8n's `get-n8n.sh` uses. Anonymous calls are limited to 60 requests/hour.
   ```
   $ gh api repos/n8n-io/n8n/releases/latest --jq '[.tag_name,.prerelease,.published_at]|@tsv'
   n8n@2.38.7	false	2026-09-11T08:06:20Z
   # unauthenticated equivalent:
   $ curl -s https://api.github.com/repos/n8n-io/n8n/releases/latest | jq -r .tag_name
   ```
   [get-n8n.sh](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/get-n8n.sh) `resolve_n8n_version()` parses `"tag_name": "n8n@X.Y.Z"` from that URL, with `FALLBACK_N8N_VERSION="2.32.0"`. It pins the result in `.env`: "never a floating tag, which would silently upgrade (and run DB migrations) on any container recreate".
2. **npm dist-tags.**
   ```
   $ curl -s https://registry.npmjs.org/-/package/n8n/dist-tags
   {"next":"2.39.4","beta":"2.39.4","stable":"2.38.7","latest":"2.38.7","rc":"2.39.4"}
   ```
3. **Docker Hub: resolve `stable` to a version by digest, or by label.**
   ```
   $ curl -s https://hub.docker.com/v2/repositories/n8nio/n8n/tags/stable | jq -r '.digest,.tag_last_pushed'
   sha256:a8c95f75c6fd…   2026-09-11T08:14:12.342095Z
   $ curl -s https://hub.docker.com/v2/repositories/n8nio/n8n/tags/2.38.7 | jq -r .digest
   sha256:a8c95f75c6fd…
   $ docker buildx imagetools inspect n8nio/n8n:2.38.7 --format '{{json .Image}}'   # config label
   … "org.opencontainers.image.version":"2.38.7" …
   ```
4. **Git pointer tag.**
   ```
   $ gh api repos/n8n-io/n8n/git/ref/tags/stable --jq .object.sha
   a2d0f7638bbb7582e33a4dfa1537eeb8ff066788        # == git/ref/tags/n8n@2.38.7
   ```

**Recommendation.**
- Take `releases/latest.tag_name`, require `^n8n@2\.`, and confirm `hub.docker.com/v2/repositories/n8nio/n8n/tags/<version>` exists.
- Optionally assert it equals the `stable` digest. This can lag by ~2–8 min; see ordering below.
- Rebuild when the version **or** the upstream index digest changes.
- Do **not** compute "max semver of non-prerelease GitHub releases". The `2.38.1` `prerelease=false` anomaly would have selected a beta-line version during 2026-09-01…09-07, while stable was 2.37.x.

Observed publish ordering:

| Release | Docker `X.Y.Z` | GitHub release | Docker `stable`/`latest` |
|---|---|---|---|
| 2.38.6 | 08:00:20Z | 08:08:03Z | 08:10:01Z |
| 2.38.7 | 07:58:12Z | 08:06:20Z | 08:14:12Z |

### 1.6 Cadence

- **Minors** (`X.Y.0`, npm time): 2.34.0 2026-08-04, 2.35.0 08-11, 2.36.0 08-18, 2.37.0 08-25, 2.38.0 09-01, 2.39.0 09-08. That is every Tuesday, ~07:17–08:44 UTC.
- **Patches**: several per week on both the beta and stable lines (2.37.x reached .11, 2.38.x .7).
- **1.123.x**: ~1–4/week (e.g. 08-12, 08-13, 08-17, 08-19, 08-20, 08-21, 09-02, 09-03, 09-09, 09-10).
- **Nightly**: `nightly` is built from master daily at 00:00 UTC (`schedule` in [docker-build-push.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/docker-build-push.yml)).
- Docs advise updating "at least once a month" ([Update n8n](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/update-n8n)).

### 1.7 n8n 3.x

**Docs** ([v3.0 breaking changes](https://docs.n8n.io/changelog/v30-breaking-changes)):
- 3.0 is "scheduled for October 2026".
- Self-hosting will require Docker: npm/`npx n8n` will no longer be supported.
- Legacy nodes are removed (Function, Function Item, Item Lists, LangChain Code), plus AI Agent v1 modes and `$getPairedItem`.
- Key rotation will be on by default.
- Compression node limits drop: 2 GiB → 256 MiB, 5000 → 1000 entries.
- Source comment: `N8N_RUNNERS_TASK_TIMEOUT` default 300 s "n8n v3 will reduce this to `60`" ([runners.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/runners.config.ts)).

**Branch.** `3.x` is "master + breaking-change commits", kept current by replaying 3.x-only commits on master ([sync-master-to-3x.mjs](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/scripts/sync-master-to-3x.mjs)).

**Images** ([build-v3-nightly.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/build-v3-nightly.yml)):
- Built daily at 08:00 UTC from `ref: '3.x'`: `n8nio/n8n:v3-nightly`, `v3-nightly-<date>`, `v3-nightly-<sha7>` (plus `-pc` and runners images).
- On Mondays (or `force_rc`) the same manifests are retagged `v3-rc`, `v3-rc-<date>` and `v3-rc-<date>.N`.
- Verified `v3-nightly` config: same DHI `26.7.0-alpine3.24-dev` base, `USER node`, same entrypoint, `N8N_RELEASE_TYPE=nightly`.

**Will `latest`/`stable`/`releases/latest` move to 3.x?**
- There is no primary-source statement.
- The current pipeline cannot release a major, and `latest`/`next` are slated for removal "in a future major version".
- By the existing track model a new line enters `beta`, becomes `stable` when the next minor ships, and the old major keeps a `vN` maintenance pointer (precedent: `v1`).
- So expect `stable`, and with it GitHub `releases/latest`, to move to 3.x eventually.
- 2.0 precedent is ambiguous. `n8n@2.0.0` (2025-12-08) is `prerelease=false`; 2.0.1, 2.1.0, 2.1.1 and 2.2.0 are `true`; 2.0.2 and 2.2.1 are `false`. `n8n@1.123.4` (2025-12-08) and `1.123.10` (2026-01-02) are `false`.
- **Update detection must pin major 2 explicitly.**

### 1.8 Docker Hub tag families, per-arch tags, re-pushes

About 4,949 tags existed on 2026-09-10.

| Pattern | What it is | Consume? |
|---|---|---|
| `X.Y.Z` | Release. OCI image index (`application/vnd.oci.image.index.v1+json`) with linux/amd64 + linux/arm64, merged via `imagetools create` from `-amd64`/`-arm64` | **yes** (or its digest) |
| `X.Y.Z-<sha7>` | Same content as `X.Y.Z` at build time; workflow comment: "immutable references for deployments" | optional |
| `X.Y.Z-amd64`, `X.Y.Z-arm64`, `X.Y.Z-<sha7>-amd64` … | Single-platform build outputs (Docker Hub reports a single-platform image) | no |
| `X.Y.Z-pc`, `X.Y.Z-<sha7>-pc`, `…-pc-amd64` | Pointer-compressed variant (§1.9) | no |
| `stable`=`latest`, `beta`=`next` | Channel retags | not for pinned builds |
| `nightly`, `nightly-<sha7>` | Master nightly | no |
| `v3-nightly*`, `v3-rc*` | 3.x branch builds | no |
| `1` | Stale 1.x pointer (1.123.27) | no |

There are no `2` or `2.38` tags (Docker Hub API 404). The runners image follows the same scheme, e.g. `n8nio/runners:X.Y.Z` and `X.Y.Z-distroless`.

**Version tags can be re-pushed with a new digest.** Evidence from the Docker Hub tag API and GitHub:

| Tag | Pushed | Digest |
|---|---|---|
| `2.38.0-53e208d` | 2026-09-01T07:16:45Z | `sha256:8254a07a40cc…` (original build; npm `2.38.0` 2026-09-01T07:17:44Z; PR #37475 merged 06:56Z) |
| `2.38.0-ae1b618` | 2026-09-08T07:33:02Z | `sha256:fd3494ec0a86…` |
| `2.38.0` | 2026-09-08T07:32:59Z | `sha256:fd3494ec0a86…` (image `created` 2026-09-08T07:27:48Z; second ":rocket: Release 2.38.0" PR #38024 merged 07:20Z; GitHub release `published_at` moved to 2026-09-08T07:39:53Z) |

For comparison, normal releases push once: `2.37.0` Docker 2026-08-25T09:16Z vs npm 07:50Z, and `2.0.0` Docker 2025-12-08T17:35Z vs npm 17:18Z. A documented re-release path exists for failed publishes, but it bumps the patch version ([release-recreate-failed-release.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/release-recreate-failed-release.yml)). The 2.38.0 same-version re-push is not explained by it.

**Index format changes.**
- 2.38.x indexes contain only the two platform manifests, because the build uses `--provenance=false --sbom=false` and `oci-mediatypes=true`.
- ≤2.37.11 indexes also contained `unknown/unknown` entries annotated `vnd.docker.reference.type: attestation-manifest`.
- The workflow notes that 2.26.0 shipped as a Docker manifest list and "every pull failed on older containerd (#31997)". It now asserts the OCI index format.

### 1.9 `-pc` variant

- **Bake target** `n8n-pc` ([docker-bake.hcl](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/docker-bake.hcl)):
  - Runtime `n8nio/node-pc:26.7.0@sha256:6577d074…`, builder `n8nio/node-pc:26.7.0-dev`.
  - `IMAGE_DESCRIPTION="Workflow Automation Tool (pointer-compressed variant, internal to n8n Cloud, no support or stability guarantees)"`.
- **[node-pc Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/node-pc/Dockerfile)**: Node 26.7.0 is compiled from the GPG-verified source tarball with `./configure --experimental-enable-pointer-compression`. The resulting binaries are swapped into `n8nio/base:26.7.0` ("No official pointer-compressed Node binaries exist").
- **[Image README](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/README.md)**, "About `-pc` tags": "internal to n8n Cloud. They carry no support or stability guarantees and can change or disappear without notice. Use the regular tags instead."
- **Empirical diff** (`2.38.6` vs `2.38.6-pc`):
  - Same config, env, user, entrypoint and DHI base.
  - Size: 1,999,669,683 vs 2,233,665,751 bytes.
  - Node location: `/usr/bin/node` (stock) vs `/usr/local/bin/node` (compiled; `/usr/bin/node` symlinks to it).
  - `process.config.variables.v8_enable_pointer_compression`: `0` vs `1`.
  - Same description label except the `-pc` suffix text. Both report `heap_size_limit` 2144 MB.

### 1.10 GHCR and docker.n8n.io

- **GHCR.** The same pipeline pushes `ghcr.io/n8n-io/n8n:<version>` and `ghcr.io/n8n-io/runners:<version>`.
  - `ghcr.io/n8n-io/n8n:2.38.6` has `docker-content-digest: sha256:7406a977…`, identical to Docker Hub.
  - GHCR has `latest`, `stable`, `beta`, `next` and `nightly`.
  - n8n's own [get-n8n-compose.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/get-n8n-compose.yml) mixes the registries: `docker.io/n8nio/n8n` and `ghcr.io/n8n-io/runners`.
- **docker.n8n.io** is used in the image README and in n8n-hosting (`docker.n8n.io/n8nio/n8n:${N8N_VERSION}`).
  - The docs.n8n.io install pages use plain `n8nio/n8n` instead.
  - `https://docker.n8n.io/v2/` answers with `www-authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:n8nio/n8n:pull"`, i.e. it fronts Docker Hub `n8nio/n8n`.
  - A digest comparison attempt returned HTTP 429, so this mapping is not digest-verified.

---

## 2. Image construction (tag `n8n@2.38.6`, commit 0e7a133; unchanged in `n8n@2.38.7`)

### 2.1 Build chain

**1. Base image `n8nio/base:26.7.0`** ([n8n-base Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n-base/Dockerfile), built by `build-base-image.yml`).
- `FROM ${DHI_REF}`. Bake sets `DHI_REF=dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f`. The Dockerfile's own default is `dhi.io/node:24.19.0-alpine3.24-dev`.
- `apk add --no-cache busybox-binsh`.
- Microsoft core fonts via `msttcorefonts-installer fontconfig`, then the installer is removed.
- `apk add --no-cache openssh graphicsmagick tini tzdata ca-certificates libc6-compat librdkafka`.
  - git and libssl3/libcrypto3 come from the DHI base.
  - No blanket `apk upgrade`: "patched bytes come from bumping the pinned DHI digest instead".
- Cleanup, then **`apk del apk-tools`**.
- `ln -sf /usr/bin/node /usr/local/bin/node`, `WORKDIR /home/node`, `ENV NODE_PATH=/usr/local/lib/node_modules`, `EXPOSE 5678/tcp`.

**2. `n8nio/n8n`** ([Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/Dockerfile)).
- Build stages `FROM node:26.7.0-alpine3.24@sha256:aadf416b…` (+ `python3 make g++ librdkafka-dev`) recompile the native modules `isolated-vm`, `sqlite3` and `@confluentinc/kafka-javascript`. Comment: DHI Alpine lacks `/etc/alpine-release`, so `node-gyp-build` would load glibc prebuilds.
- Final stage `FROM n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8`:
  - `ARG N8N_VERSION`, `ARG N8N_RELEASE_TYPE=dev` (CI passes `stable`/`rc`/`nightly`), `ARG IMAGE_DESCRIPTION`.
  - `ENV NODE_ENV=production`, `ENV N8N_RELEASE_TYPE=${N8N_RELEASE_TYPE}`, `ENV SHELL=/bin/sh`.
  - `WORKDIR /home/node`.
  - `COPY --link ./compiled /usr/local/lib/node_modules/n8n` and `COPY --link docker/images/n8n/docker-entrypoint.sh /`, plus the native `.node` files from the builder.
  - `RUN`: `ln -s $N8N/bin/n8n /usr/local/bin/n8n`, `mkdir -p /home/node/.n8n`, `chown -R node:node /home/node`, `rm -rf /root/.npm /tmp/*`.
  - `EXPOSE 5678/tcp`, `USER node`, `ENTRYPOINT ["tini", "--", "/docker-entrypoint.sh"]`.
  - `LABEL org.opencontainers.image.title="n8n"`, `.description`, `.source="https://github.com/n8n-io/n8n"`, `.url="https://n8n.io"`, `.version=${N8N_VERSION}`.
  - **No `CMD`, `VOLUME`, `HEALTHCHECK` or `STOPSIGNAL`** (confirmed by `docker image inspect`: `Cmd=null Volumes=null Healthcheck=null`).

**3. Entrypoint** ([docker-entrypoint.sh](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/docker-entrypoint.sh)):
```sh
#!/bin/sh
if [ -d /opt/custom-certificates ]; then
  echo "Trusting custom certificates from /opt/custom-certificates."
  export NODE_OPTIONS="--use-openssl-ca $NODE_OPTIONS"
  export SSL_CERT_DIR=/opt/custom-certificates
  c_rehash /opt/custom-certificates
fi
if [ "$#" -gt 0 ]; then exec n8n "$@"; else exec n8n; fi
```
Container args are passed to `n8n`, e.g. `docker run IMAGE worker`.

**Not related:** `docker/images/engine/Dockerfile` (`node:24.18.1-alpine3.24`, port 3000) is a different service image.

### 2.2 Final image facts (empirical E2–E4, `2.38.6` amd64)

| Property | Value |
|---|---|
| OS | `PRETTY_NAME="Docker Hardened Images/Alpine Linux v3.24"`, `ID=alpine`, `VERSION_ID=3.24`; no `/etc/alpine-release` |
| libc | musl (`/lib/ld-musl-x86_64.so.1`). `gcompat` is installed (via `libc6-compat`), so `/lib64/ld-linux-x86-64.so.2` exists; `glibcVersionRuntime` is undefined |
| Node | `v26.7.0` (DHI apk `nodejs-26`), OpenSSL 3.5.7, ICU 78.3; `/usr/local/bin/node` → `/usr/bin/node` |
| User | `uid=1000(node) gid=1000(node)`, `HOME=/home/node`, WORKDIR `/home/node` |
| ENV | `NODE_VERSION=26.7.0-r0`, `NPM_CONFIG_UPDATE_NOTIFIER=false`, `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`, `NODE_PATH=/usr/local/lib/node_modules`, `NODE_ENV=production`, `N8N_RELEASE_TYPE=stable`, `SHELL=/bin/sh` |
| Labels | OCI labels above, plus inherited `com.docker.dhi.*`: `distro=alpine-3.24`, `variant=dev`, `package-manager=apk`, `shell=busybox`, `compliance=cis`, `version=26.7.0-alpine3.24-dev`, `definition=image/node/alpine-3.24/26-dev`, `entitlement=public` |
| Present | `/bin/sh`→`/bin/busybox`, `ash`, `tini` (`/sbin/tini`), `git`, `ssh`, `gm` (GraphicsMagick), `wget` (busybox), `tar`, `gzip`, `unzip`, `su`, `c_rehash`, `npm`, `npx`, `corepack`, `n8n` (`/usr/local/bin/n8n`) |
| Absent | `apk`, `apt-get`, `bash`, `python3`/`python`, `curl`, `openssl` CLI, `xz`, `sudo`, `doas`, `convert`, `pnpm`, `ffmpeg`, `ffprobe`, `yt-dlp` |
| apk state | `/sbin/apk` removed; `/usr/lib/libapk.so.3.0.0` kept. `/lib/apk/db/installed` lists 69 packages. `/etc/apk/world` is **checksum-pinned** (`libgcc><Q1…`). Repositories: `https://dhi.io/apk/alpine/v3.24/main`, `https://dl-cdn.alpinelinux.org/alpine/v3.24/main`, `…/community`. DHI and Alpine keys in `/etc/apk/keys` |
| Dirs | `/home/node` and `/home/node/.n8n`: `node:node` 755 (`.n8n` empty in image). `/usr/local/bin`, `/usr/local/lib`, `/opt`: root 755. `/tmp`: 1777 |
| Size | 1,999,669,683 bytes (uncompressed, amd64) |
| Ports | 5678/tcp (UI/API/webhooks). The task broker listens on 127.0.0.1:5679 internally |

### 2.3 Platforms, attestations, signatures

- **Platforms.** `n8nio/n8n:2.38.6` and `2.38.7` are OCI image indexes with exactly `linux/amd64` and `linux/arm64`.
  - 2.38.6 manifests: amd64 `sha256:daf782b5…`, arm64 `sha256:e2f21d85…`.
  - Branch builds are amd64-only, but those are not published to Docker Hub.
- **Attestations** ([docker-build-push.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/.github/workflows/docker-build-push.yml)). For release types `stable`/`rc`/`nightly`, CI runs these against the **GHCR** index digest:
  - `slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.1.0` (SLSA provenance);
  - `cosign attest --type openvex --predicate security/vex.openvex.json`;
  - a CycloneDX SBOM (syft v1.38.2) attested with cosign;
  - plus a Trivy scan.
- **Empirical.** GHCR tag `sha256-7406a977….att` exists, with three DSSE layers: predicate types `https://cyclonedx.org/bom`, `https://slsa.dev/provenance/v0.2` and `https://openvex.dev/ns`.
  - `.sig` returns 404 on GHCR; Docker Hub has neither `.att` nor `.sig`.
  - Because the index digest is identical on both registries, the GHCR attestations describe the Docker Hub image too.
  - Signature/identity verification (`cosign verify-attestation`) was not attempted.

### 2.4 `n8nio/runners` (sidecar; empirical E5)

- `n8nio/runners:2.38.6`:
  - `USER runner` (1000:1000), `WORKDIR /home/runner`.
  - Stock `Alpine Linux` 3.24.1, not DHI.
  - Python 3.13.15, node v26.7.0, `sh` present; `apk`, `bash`, `ffmpeg` and `yt-dlp` absent.
  - `ENTRYPOINT ["tini","--","/usr/local/bin/task-runner-launcher"]`, `CMD ["javascript","python"]`, `EXPOSE 5680/tcp`.
- **Launcher config** ([n8n-task-runners.json](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/runners/n8n-task-runners.json)):
  - JS runner `env-overrides`: `NODE_FUNCTION_ALLOW_BUILTIN=crypto`, `NODE_FUNCTION_ALLOW_EXTERNAL=moment`.
  - Python runner: `N8N_RUNNERS_STDLIB_ALLOW=""`, `N8N_RUNNERS_EXTERNAL_ALLOW=""`.
- The runners image version must match the n8n image version ([Set up task runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners)).

---

## 3. Runtime contract to preserve

### 3.1 Persistent data & encryption key

**Data folder.**
- `N8N_USER_FOLDER` unset → `path.join($HOME, '.n8n')` = `/home/node/.n8n` ([utils.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/utils/utils.ts)).
- On first start with an empty volume (E6), the folder contains:
  - `config` (mode 0600; log: `No encryption key found - Auto-generating and saving to: /home/node/.n8n/config`);
  - `database.sqlite` with `-wal`/`-shm` (2.x SQLite pooled/WAL driver);
  - `crash.journal`.
- n8n also creates `/home/node/.cache` at runtime, which is outside the usual volume.

**Binary data.**
- Default mode is `filesystem` in regular mode and `database` in queue mode.
- Path: `N8N_BINARY_DATA_STORAGE_PATH` ‖ `N8N_STORAGE_PATH` ‖ `~/.n8n/storage` ("`~/.n8n/binaryData` is no longer the default") ([binary-data.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/core/src/binary-data/binary-data.config.ts)).
- So media loaded into n8n as binary data lands in the `.n8n` volume.
- Database mode caps a single file at `N8N_BINARY_DATA_DATABASE_MAX_FILE_SIZE` = 512 MiB, max 1024 ([binary-data env docs](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/binary-data)).

**What the docs say.**
- Mount a volume at `/home/node/.n8n`. Even with PostgreSQL it "still contains other important data like encryption keys, instance logs, and source control feature assets" ([Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker)).
- The README warns: "If this data can't be found at startup n8n automatically creates a new key and any existing credentials can no longer be decrypted."

**Encryption key.**
- `N8N_ENCRYPTION_KEY`, or `N8N_ENCRYPTION_KEY_FILE` per the source comment, is used only "if the key isn't yet in the settings file".
- In queue mode it "must" be set for all workers ([custom encryption key](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key), [instance-settings-config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/instance-settings-config.ts)).

**Settings file permissions.** `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` defaults to **`true`** in 2.x (source + [v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes)). n8n checks the settings file and chmods it to 0600; set `false` only where the filesystem has no permissions (e.g. Windows).

### 3.2 Official run/Compose examples (as published)

- **[Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker)** (page flagged "This content is outdated"):
  - `docker volume create n8n_data`
  - `docker run -it --rm --name n8n -p 5678:5678 -e GENERIC_TIMEZONE=… -e TZ=… -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true -e N8N_RUNNERS_ENABLED=true -v n8n_data:/home/node/.n8n n8nio/n8n`
  - Note: `N8N_RUNNERS_ENABLED` is deprecated in 2.x.
  - Update procedure: `docker compose pull && docker compose down && docker compose up -d`.
- **[Install using Docker Compose](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose)** (recommended):
  - Services: n8n + sandbox stack (`sandbox-certs`, `sandbox-api`, privileged DinD `sandbox-runner-1`) + SearXNG.
  - No DB service: SQLite is "stored inside the container unless you mount a volume for it". Postgres 18 is optional (`PGDATA=/var/lib/postgresql/data`).
  - The compose file is embedded from GitHub and is not in the `.md` export.
  - Verification step: `curl -sf http://localhost:5678/healthz`.
- **Repo installer** [get-n8n.sh](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/get-n8n.sh) + [get-n8n-compose.yml](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/get-n8n-compose.yml) (one-line setup):
  - `n8n: image: docker.io/n8nio/n8n:${N8N_VERSION}`, `volumes: - n8n-data:/home/node/.n8n`, `env_file: .env`.
  - `runners: image: ghcr.io/n8n-io/runners:${N8N_VERSION}` with `N8N_RUNNERS_TASK_BROKER_URI: http://n8n:5679` and `N8N_RUNNERS_AUTO_SHUTDOWN_TIMEOUT: '15'`.
  - The generated `.env` sets `N8N_VERSION=<pinned>`, `N8N_RUNNERS_MODE=external`, `N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0` and a random `N8N_RUNNERS_AUTH_TOKEN`.
- **[Use Docker Compose](https://docs.n8n.io/deploy/host-n8n/install-options/use-a-cloud-provider/use-docker-compose)** (Traefik):
  - `image: n8nio/n8n`, `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true`, `N8N_RESTRICT_FILE_ACCESS_TO=/files`.
  - Volumes `n8n_data:/home/node/.n8n` and bind `./local-files:/files` ("use the `/files` path").
- **[n8n-hosting](https://github.com/n8n-io/n8n-hosting)** (not archived; pushed 2026-09-10), [`docker-compose/withPostgres` @2581d14](https://github.com/n8n-io/n8n-hosting/blob/2581d14/docker-compose/withPostgres/docker-compose.yml):
  - `image: docker.n8n.io/n8nio/n8n:${N8N_VERSION}`, `n8n_storage:/home/node/.n8n`.
  - `N8N_RUNNERS_MODE=external`, `N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0`.
  - Sidecar `n8nio/runners:${N8N_VERSION}`.
  - `postgres:18` with a non-root DB user.
  - Other examples: `withPostgresAndWorker`, `subfolderWithSSL`.

### 3.3 File-permission pitfalls

- n8n runs as uid/gid **1000**. Bind mounts (data dir, media dir) must be writable by 1000.
- A new named volume mounted on `/home/node/.n8n` is populated from the image directory (general Docker behaviour), so it inherits `node:node`. A derived image must keep `/home/node/.n8n` owned by `node` and must not declare a `VOLUME` that changes this.
- The 0600 settings-file enforcement is on by default (§3.1).
- Docs WSL note: keep project dirs inside the WSL filesystem, not `/mnt/c/...`, to avoid permission issues ([Install using Docker Compose](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose)).

### 3.4 Health endpoints

- **`GET /healthz`** → `200 {"status":"ok"}`. It is always enabled on the main server and "doesn't indicate DB status".
- **`GET /healthz/readiness`** → `200 {"status":"ok"}` only when `connected && migrated && fullyReady`, otherwise `503 {"status":"error"}` ([abstract-server.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/cli/src/abstract-server.ts), [Monitor n8n](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/monitor-n8n)). Observed 503 during first-start migrations, then 200 (E6).
- **Path**: `N8N_ENDPOINT_HEALTH`, default `'/healthz'` ([endpoints.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/endpoints.config.ts)).
- **Queue workers**: `QUEUE_HEALTH_CHECK_ACTIVE` defaults to `false` ([scaling-mode.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/scaling-mode.config.ts)); `QUEUE_HEALTH_CHECK_PORT` defaults to 5678 ([queue-mode env](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/queue-mode)).
- **`/metrics`** requires `N8N_METRICS=true`. A settled 2.38.7 instance without it returned `404 Cannot GET /metrics`.
- **No image HEALTHCHECK.** Busybox `wget` is available (docs use `docker compose exec n8n wget -qO- …`); `curl` is not.

### 3.5 Minimal CI smoke test (pattern exercised in E6/E7)

```sh
docker run -d --name n8n-smoke -p 127.0.0.1:5678:5678 IMAGE          # no env needed; ephemeral SQLite + auto key
curl -s --retry 40 --retry-delay 2 --retry-connrefused --retry-all-errors \
     -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5678/healthz/readiness   # → 200 once migrated
docker exec n8n-smoke sh -c 'n8n --version && yt-dlp --version && ffmpeg -version && ffprobe -version'
docker rm -f n8n-smoke
```

For an end-to-end Execute Command test without the UI, see E7:
- Import a workflow JSON that includes an `id`: `n8n import:workflow --input=wf.json`.
- Run it with `n8n execute --id <id> --rawOutput` in a container started with `NODES_EXCLUDE=[]`.
- In 2.x, `n8n execute --file` no longer works: it prints `"--id" has to be set!`.

---

## 4. 2.x changes affecting running yt-dlp/ffmpeg from workflows

### 4.1 Execute Command disabled by default

- **Source.** [nodes.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/nodes.config.ts): `@Env('NODES_EXCLUDE') exclude: JsonStringArray = ['n8n-nodes-base.executeCommand', 'n8n-nodes-base.localFileTrigger'];`.
  - Invalid JSON, or a non-string array, parses to `[]`, which **enables all nodes** (the `JsonStringArray` constructor catches the parse error and returns `[]`).
- **Docs.** [v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes) and [Block specific nodes](https://docs.n8n.io/deploy/host-n8n/configure-n8n/security/block-specific-nodes): "set `NODES_EXCLUDE="[]"` to enable all nodes, or remove only the specific nodes you need".
  - The [nodes env reference](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/nodes) lists the same default.
- **How to re-enable.** Compose: `NODES_EXCLUDE: '["n8n-nodes-base.localFileTrigger"]'` (keeps LocalFileTrigger blocked) or `NODES_EXCLUDE: '[]'`.
  - Setting the variable replaces the whole default list.
- **Empirical (E7).** Default env gives `Unrecognized node type: n8n-nodes-base.executeCommand`. With `NODES_EXCLUDE=[]` the node ran with `exitCode 0`.
- Docs: the node "isn't available on n8n Cloud".

### 4.2 Where Execute Command executes

- **Source** ([ExecuteCommand.node.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/nodes-base/nodes/ExecuteCommand/ExecuteCommand.node.ts)): `import { spawn } from 'child_process'` … `spawn(command, { cwd: process.cwd(), shell: true, detached })`.
  - It runs in the n8n Node process with no `env` option, so the container environment is inherited. It does not use a task runner.
- **Docs** ([Execute Command](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand)):
  - "If you run n8n with Docker, your command will run in the n8n container and not the Docker host."
  - "If you're using queue mode, the command runs on the worker that's executing the task in production mode. When running manual executions, it runs on the main instance, unless you set `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS` to `true`."
- **Empirical (E7).** stdout was `uid=1000(node) gid=1000(node) …\n/home/node\nSHELL=/bin/sh\n/bin/busybox\nno-ffmpeg-no-ytdlp`.
  - The command runs as `node`, cwd `/home/node`, under busybox `sh` (not bash). Stock image: no ffmpeg or yt-dlp.
- **Consequence.** Binaries belong in the `n8nio/n8n`-derived image, used for main **and** every queue-mode worker. `NODES_EXCLUDE` must be set on workers too; this is inferred from per-process node loading and not separately verified.

### 4.3 Can the Code node spawn processes?

- **Task runners.** Code node JS/Python executes in a task runner. The runner is launched with `--disallow-code-generation-from-strings --disable-proto=delete` (E6 process list; [n8n-task-runners.json](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/runners/n8n-task-runners.json)).
- **Allowlist.** `NODE_FUNCTION_ALLOW_BUILTIN` default `''` ([js-runner-config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/task-runner/src/config/js-runner-config.ts)). Docs: "Use * to allow all. n8n disables importing modules by default."
- **Internal mode.** n8n passes `NODE_FUNCTION_ALLOW_BUILTIN`, `NODE_FUNCTION_ALLOW_EXTERNAL`, `PATH` and `HOME` from its own env to the runner child process ([task-runner-process-js.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/cli/src/task-runners/task-runner-process-js.ts)).
  - Empirical (E7): the default gives `Module 'child_process' is disallowed [line 1]`.
  - With `NODE_FUNCTION_ALLOW_BUILTIN=child_process`, `execSync('id; command -v sh')` returned `uid=1000(node)…\n/bin/sh`: same container, same binaries.
- **External mode.** Set the allowlist in the runners container's `/etc/n8n-task-runners.json` `env-overrides` (default `crypto`) ([task-runners env](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/task-runners)). The binaries would then have to exist in the **runners** image (§2.4).
- **Security.** Docs warn that internal mode is insecure by design ("Task runners are the only isolation layer…", "use external mode" in production) ([Set up task runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners)).

### 4.4 Task runner defaults

- **Enabled by default** in 2.x ([v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes)). `N8N_RUNNERS_ENABLED` is deprecated ("You no longer need to set it").
- **Settings** ([runners.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/runners.config.ts)):

  | Variable | Default |
  |---|---|
  | `N8N_RUNNERS_MODE` | `internal` |
  | `N8N_RUNNERS_BROKER_PORT` | `5679` |
  | `N8N_RUNNERS_BROKER_LISTEN_ADDRESS` | `127.0.0.1` |
  | `N8N_RUNNERS_MAX_CONCURRENCY` | `10` |
  | `N8N_RUNNERS_TASK_TIMEOUT` | `300` (v3 → 60) |
  | `N8N_RUNNERS_TASK_REQUEST_TIMEOUT` | `60` |
  | `N8N_RUNNERS_INSECURE_MODE` | `false` |

- **Separate runners image.** `n8nio/n8n` no longer contains the external-mode task runner; use `n8nio/runners` with the same version. Python Code nodes need external mode. The stock n8n image logs `Failed to start Python task runner in internal mode. because Python 3 is missing` (E6).
- **Queue mode.** Each worker needs its own runners sidecar in external mode.
- **Does a custom binary need to be in `n8nio/runners`?** Only for Code-node code that spawns it in external mode. Execute Command and all other nodes run in the n8n process.

### 4.5 File-system restrictions (Read/Write Files from Disk, Read Binary Files)

- **Source** ([security.config.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/@n8n/config/src/configs/security.config.ts)):
  - `N8N_RESTRICT_FILE_ACCESS_TO` default `'~/.n8n-files'`. Multiple dirs are separated by `;`; the empty string disables restrictions ("insecure").
  - `N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES` default `true`. It blocks `~/.n8n`, `~/.cache/n8n/public`, and dirs from `N8N_CONFIG_FILES`, `N8N_CUSTOM_EXTENSIONS`, `N8N_BINARY_DATA_STORAGE_PATH`, `N8N_UM_EMAIL_TEMPLATES_INVITE` and `UM_EMAIL_TEMPLATES_PWRESET`.
  - `N8N_BLOCK_FILE_PATTERNS` default `^(?:[^/]*/)*\.git(?:/.*)?$`.
  - These settings apply to the `ReadWriteFile` and `ReadBinaryFiles` nodes. They do not constrain shell commands in Execute Command (inference from the source comment).
- **Docs** ([v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes), [Read/Write Files from Disk](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile)): the default is `~/.n8n-files`; "paths refer to the n8n container's filesystem".
- **Empirical (E6/E7).**
  - `/home/node/.n8n-files` does not exist in the image or after first start.
  - Reading `/tmp/media/probe.txt` gives `NodeApiError: Access to the file is not allowed.`
  - Reading `/home/node/.n8n-files/probe.txt` gives `status: success`.
- **Implication for yt-dlp workflows.** Either download into `/home/node/.n8n-files/…` (create or mount it, writable by 1000) or set `N8N_RESTRICT_FILE_ACCESS_TO` to the mounted media dir, as the Traefik example does with `/files`. Never use a path inside `~/.n8n`.

### 4.6 Other 2.x defaults that matter here

- **`N8N_BLOCK_ENV_ACCESS_IN_NODE`** is effectively **true**: access is blocked unless the value is exactly `'false'` ([workflow-data-proxy-env-provider.ts](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/packages/workflow/src/workflow-data-proxy-env-provider.ts)). `$env` in expressions/Code nodes fails with "access to env vars denied". Shell commands still inherit the environment (§4.2).
- **Binary data**: `filesystem` (regular) / `database` (queue, 512 MiB per-file cap). The in-memory `default` mode was removed ([v2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes)). Large media in queue mode needs filesystem/S3 configuration.
- **`N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true`** (§3.1).
- **`N8N_GIT_NODE_DISABLE_BARE_REPOS=true`**; OAuth callbacks require auth.
- **Removed or changed in 2.0**: the Start node; Activate→Publish; MySQL/MariaDB backends; `N8N_CONFIG_FILES`; `--tunnel`; `QUEUE_WORKER_MAX_STALLED_COUNT`.
- **CLI**: `n8n execute` requires `--id` (E7).
- **Deprecation warnings** printed by 2.38.x at start (E6):
  - `N8N_UNVERIFIED_PACKAGES_ENABLED` default will become `false`;
  - `N8N_RUNNERS_TASK_TIMEOUT` 300→60;
  - `N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES` 2 GiB→256 MiB;
  - `N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES` 5000→1000.

---

## 5. Extending the image

**Official guidance.**
- [Execute Command → Run cURL command](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand) is the only official `FROM n8nio/n8n` recipe:
  - "build a Docker image based on the existing n8n image. The default n8n Docker image uses Alpine Linux."
  - "The `apk` package manager was removed from the official n8n Docker image. To install a package like `curl`, you need to restore `apk` from a fresh Alpine base image first":
  ```dockerfile
  FROM n8nio/n8n
  USER root
  # Restore the apk package manager (removed from the base image)
  COPY --from=alpine:3.22 /sbin/apk /sbin/apk
  COPY --from=alpine:3.22 /lib/apk /lib/apk
  COPY --from=alpine:3.22 /usr/lib/libapk* /usr/lib/
  RUN apk add --no-cache curl
  USER node
  ```
- [Set up task runners → Adding extra dependencies](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners) documents extending `n8nio/runners` (≥1.121.0):
  - `USER root` → `pnpm add …` / `uv pip install …` → `COPY n8n-task-runners.json /etc/n8n-task-runners.json` → `USER runner`.
  - Packages must also be allowlisted.
- No page states that custom derived images are unsupported. The only explicit "no support" statement concerns `-pc` tags.

**The documented recipe no longer works (E9).**
- On `n8nio/n8n:2.38.7`, the snippet exits 15 with `alpine:3.22`, and also with `alpine:3.24`:
  `ERROR: unable to select packages: libgcc-15.2.0-r7: breaks: world[libgcc><Q1MXMOILmYhfBnpkNyfdeOVg9oHog=] … libstdc++ … libexpat … git … git-init-template …`
- Cause: `COPY /lib/apk` overwrites the image's DHI package DB (69 packages) with stock Alpine's (16 packages), while `/etc/apk/world` keeps DHI checksum pins.
- Using only the dl-cdn repos fails the same way (exit 72).
- Stripping the pins (`sed -i 's/><Q1[^ ]*//' /etc/apk/world`) let `apk add ffmpeg` proceed. However, apk then **purged** `alpine-baselayout`, `alpine-release`, `alpine-keys`, `apk-tools`, `musl-utils` and `scanelf`. Unsafe.

**Non-official variant that worked (E9).** Keep the image's own apk DB and restore only the binary:
```dockerfile
FROM n8nio/n8n:2.38.7
USER root
COPY --from=alpine:3.24 /sbin/apk /sbin/apk
COPY --from=alpine:3.24 /usr/lib/libapk* /usr/lib/
RUN apk add --no-cache ffmpeg
USER node
```
- Result: `OK: 302.6 MiB in 166 packages`; `ffmpeg version 8.1.2`, `ffprobe version 8.1.2`.
- Node `v26.7.0` crypto OK; `n8n --version` → `2.38.7`; still `USER node`.
- Image size 2,174,091,304 bytes.
- The Alpine minor must match the image's DHI Alpine (`com.docker.dhi.distro=alpine-3.24`). Packages come from the image's configured repos (`dhi.io/apk/alpine/v3.24/main` is publicly reachable, plus dl-cdn v3.24 main/community).

**Caveats for a derived image (from the sources above).**
- **Keep the runtime contract.** Keep `USER node` at the end, don't override `ENTRYPOINT` (tini + custom-cert handling), don't add `CMD`, keep `WORKDIR /home/node`, and don't `VOLUME` or `chown` away `/home/node/.n8n`.
- **Base contents move with n8n releases.** The base is pinned by digest per n8n release (`RUNTIME_IMAGE=n8nio/base:26.7.0@sha256:…`). Alpine minor, Node major and installed libs change only when n8n bumps that pin, so derived builds should re-resolve per upstream version.
- **Plan for the shell and libc.** The image has musl only; glibc-linked binaries rely on `gcompat`. The shell is busybox `sh`.
- **Tag with the upstream version.** Use the exact upstream n8n version in the derived tag, so `n8nio/runners:<same version>` can be paired in external mode.

---

## Empirical checks

All commands ran on 2026-09-10/11 (linux/amd64). Output is trimmed.

**E1: registry and release state** (2026-09-11)
```
$ gh api 'repos/n8n-io/n8n/releases?per_page=12' --jq '.[]|[.tag_name,"prerelease="+(.prerelease|tostring),.published_at]|@tsv'
stable      prerelease=false 2026-09-11T08:06:22Z
n8n@2.38.7  prerelease=false 2026-09-11T08:06:20Z
n8n@2.39.4  prerelease=true  2026-09-11T08:29:50Z
n8n@2.39.3  prerelease=true  2026-09-11T07:45:02Z
beta        prerelease=true  2026-09-11T08:29:51Z
n8n@2.38.6  prerelease=false 2026-09-10T08:08:03Z
n8n@1.123.79 prerelease=false 2026-09-10T06:26:27Z
…
$ gh api 'repos/n8n-io/n8n/git/matching-refs/tags/n8n@3' --jq length      → 0
$ gh api repos/n8n-io/n8n/branches/3.x --jq '.commit.sha[0:7]'           → a496f5a
$ for t in 2 2.38 1; do curl -s -o /dev/null -w "$t %{http_code}\n" https://hub.docker.com/v2/repositories/n8nio/n8n/tags/$t; done
2 404 / 2.38 404 / 1 200   (tag 1 → org.opencontainers.image.version 1.123.27, pushed 2026-03-25)
$ docker buildx imagetools inspect --raw n8nio/n8n:2.38.6
{"mediaType":"application/vnd.oci.image.index.v1+json","manifests":[
  {"digest":"sha256:daf782b5…","platform":{"architecture":"amd64","os":"linux"}},
  {"digest":"sha256:e2f21d85…","platform":{"architecture":"arm64","os":"linux"}}]}
$ docker buildx imagetools inspect --raw n8nio/n8n:2.37.11   # older format
… {'architecture':'unknown','os':'unknown'} {'vnd.docker.reference.type':'attestation-manifest'} …
```

**E2: image config** (`docker image inspect n8nio/n8n:2.38.6 --format '{{json .Config}}'`)
```
"User":"node","ExposedPorts":{"5678/tcp":{}},
"Env":["NODE_VERSION=26.7.0-r0","NPM_CONFIG_UPDATE_NOTIFIER=false","PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
       "NODE_PATH=/usr/local/lib/node_modules","NODE_ENV=production","N8N_RELEASE_TYPE=stable","SHELL=/bin/sh"],
"Entrypoint":["tini","--","/docker-entrypoint.sh"],"WorkingDir":"/home/node",
"Labels":{"com.docker.dhi.distro":"alpine-3.24","com.docker.dhi.package-manager":"apk","com.docker.dhi.shell":"busybox",
          "com.docker.dhi.version":"26.7.0-alpine3.24-dev","org.opencontainers.image.version":"2.38.6",…}
Healthcheck=null Volumes=null Cmd=null StopSignal=""   Size=1999669683
```
2.38.7 (`imagetools inspect --format '{{json .Image}}'`) has the same user, entrypoint, env and DHI version, the label `2.38.7`, and amd64+arm64.

**E3: inside the container**
```
$ docker run --rm --entrypoint sh n8nio/n8n:2.38.6 -c '…'
PRETTY_NAME="Docker Hardened Images/Alpine Linux v3.24"      cat: can't open '/etc/alpine-release'
uid=1000(node) gid=1000(node) groups=1000(node),1000(node)
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin  SHELL=/bin/sh HOME=/home/node  pwd=/home/node
apk: MISSING  apt-get: MISSING  python3: MISSING  bash: MISSING  curl: MISSING  openssl: MISSING  ffmpeg/ffprobe/yt-dlp: MISSING
sh: /bin/sh  busybox: /bin/busybox  tini: /sbin/tini  git: /usr/bin/git  ssh: /usr/bin/ssh  gm: /usr/bin/gm  wget: /usr/bin/wget
node: /usr/local/bin/node  npm: /usr/bin/npm  c_rehash: /usr/bin/c_rehash  su: /bin/su  unzip: /usr/bin/unzip
v26.7.0   openssl 3.5.7 icu=78.3 glibcVersionRuntime=undefined
/lib/ld-musl-x86_64.so.1   /lib64: ld-linux-x86-64.so.2   /bin/sh -> /bin/busybox
/home/node: drwxr-xr-x node node .n8n (empty)     /usr/local/bin: n8n -> /usr/local/lib/node_modules/n8n/bin/n8n, node -> /usr/bin/node
n8n --version → 2.38.6
$ docker run --rm --entrypoint sh n8nio/n8n:2.38.7 -c 'cat /etc/apk/repositories; grep -c "^P:" /lib/apk/db/installed'
https://dhi.io/apk/alpine/v3.24/main
https://dl-cdn.alpinelinux.org/alpine/v3.24/main
https://dl-cdn.alpinelinux.org/alpine/v3.24/community
69            (alpine:3.24 → 16)
```

**E4: `-pc` vs plain**
```
n8nio/n8n:2.38.6     Size=1999669683 /usr/bin/node (file)                  pointer_compression=0 heap_limit_MB=2144
n8nio/n8n:2.38.6-pc  Size=2233665751 /usr/local/bin/node (file, /usr/bin/node -> it) pointer_compression=1 heap_limit_MB=2144
desc(-pc)="Workflow Automation Tool (pointer-compressed variant, internal to n8n Cloud, no support or stability guarantees)"
```

**E5: runners image**
```
$ docker image inspect n8nio/runners:2.38.6 …  User=runner Entrypoint=["tini","--","/usr/local/bin/task-runner-launcher"] Cmd=["javascript","python"] Expose=5680
NAME="Alpine Linux" VERSION_ID=3.24.1  uid=1000(runner)  apk: MISSING  python3: /usr/local/bin/python3  node v26.7.0  ffmpeg/yt-dlp: MISSING
```

**E6: startup, health, processes** (`docker run -d -p 127.0.0.1:15678:5678 n8nio/n8n:2.38.6`)
```
/healthz            → HTTP/1.1 200 OK {"status":"ok"}
/healthz/readiness  → HTTP/1.1 503 {"status":"error"}   (during migrations) … later 200
PID 1 node tini -- /docker-entrypoint.sh
PID 7 node node /usr/local/bin/n8n
PID 33 node node --disallow-code-generation-from-strings --disable-proto=delete …/@n8n/task-runner…   (internal JS runner)
/home/node/.n8n: -rw------- config, database.sqlite(+-shm,-wal), crash.journal ; /home/node/.cache created ; /home/node/.n8n-files: No such file or directory
log: No encryption key found - Auto-generating and saving to: /home/node/.n8n/config
log: n8n ready on ::, port 5678 / n8n Task Broker ready on 127.0.0.1, port 5679
log: Failed to start Python task runner in internal mode. because Python 3 is missing from this system…
log: deprecations: N8N_UNVERIFIED_PACKAGES_ENABLED, N8N_RUNNERS_TASK_TIMEOUT (300→60), N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES, N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES
2.38.7 settled instance: /healthz/readiness → 200 ; /metrics → HTTP/1.1 404 "Cannot GET /metrics"
```

**E7: node behaviour via CLI.** Workflows were imported with `n8n import:workflow --input=/wf/<f>.json`, then run with `n8n execute --id <id> --rawOutput`.
```
n8n execute --file /wf/exec.json           → "--id" has to be set!
[default env]
executeCommand                              → Unrecognized node type: n8n-nodes-base.executeCommand
readWriteFile read /tmp/media/probe.txt     → NodeApiError: Access to the file is not allowed.
readWriteFile read /home/node/.n8n-files/probe.txt → "status": "success"
code: require('child_process')              → Module 'child_process' is disallowed [line 1]
[-e NODES_EXCLUDE=[] -e NODE_FUNCTION_ALLOW_BUILTIN=child_process]
executeCommand "id; pwd; echo SHELL=$SHELL; readlink /bin/sh; command -v ffmpeg yt-dlp || echo no-ffmpeg-no-ytdlp"
  → "exitCode": 0, "stdout": "uid=1000(node) gid=1000(node) groups=1000(node),1000(node)\n/home/node\nSHELL=/bin/sh\n/bin/busybox\nno-ffmpeg-no-ytdlp"
code: execSync('id; command -v sh')         → "out": "uid=1000(node) gid=1000(node) …\n/bin/sh\n"
```

**E8: tag re-push and attestations**
```
$ curl -s 'https://hub.docker.com/v2/repositories/n8nio/n8n/tags?page_size=100&name=2.38.0' | …
2.38.0          2026-09-08T07:32:59Z sha256:fd3494ec0a86
2.38.0-ae1b618  2026-09-08T07:33:02Z sha256:fd3494ec0a86
2.38.0-53e208d  2026-09-01T07:16:45Z sha256:8254a07a40cc
GHCR  ghcr.io/n8n-io/n8n:2.38.6 docker-content-digest: sha256:7406a977895d0158ab0f5b2a3dc66de636711f36c06f0e2e2b1c391fc91f8ec3
GHCR  …/manifests/sha256-7406a977….att → 200 ; .sig → 404 ; layers predicateType: https://cyclonedx.org/bom, https://slsa.dev/provenance/v0.2, https://openvex.dev/ns
DockerHub tags sha256-7406a977….att / .sig → 404
```

**E9: extending with apk** (base `n8nio/n8n:2.38.7`)
```
docs snippet (alpine:3.22)         → RUN apk add --no-cache curl … exit code: 15
docs snippet (alpine:3.24)         → ERROR: unable to select packages: libgcc-15.2.0-r7: breaks: world[libgcc><Q1MXMOILmYhfBnpkNyfdeOVg9oHog=] … exit 15
+ --repositories-file /dev/null -X dl-cdn main -X dl-cdn community → unable to select packages … exit 72
copy /lib/apk + unpin world + apk add ffmpeg → (1/162) Purging alpine-baselayout … Purging apk-tools (3.0.6-r0) … OK: 303.1 MiB in 166 packages; the same RUN's next `apk info` failed → no image
copy only /sbin/apk + /usr/lib/libapk* (alpine:3.24), apk add --no-cache ffmpeg → OK: 302.6 MiB in 166 packages
  run: node | ffmpeg version 8.1.2 | ffprobe version 8.1.2 | node ok v26.7.0 | 2.38.7 | apk-tools 3.0.6-r0 ; Size=2174091304
```

---

## Conflicts / uncertainties

**Env-var reference tables disagree with 2.x source and the 2.0 breaking-changes page.** In each case source and empirical behaviour win.

| Variable | Env-var reference table says | 2.x source / 2.0 page |
|---|---|---|
| `N8N_RESTRICT_FILE_ACCESS_TO` | empty ([security env](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/security)) | `~/.n8n-files` |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | `false` | blocked unless `'false'`; 2.0 page says `true` |
| `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` | `false` | `true` |
| `N8N_DEFAULT_BINARY_DATA_MODE` | `default` ([binary-data env](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/binary-data)) | mode removed in 2.0; `filesystem`/`database` |
| `N8N_BINARY_DATA_STORAGE_PATH` | `N8N_USER_FOLDER/binaryData` | `~/.n8n/storage` |
| `N8N_ENDPOINT_HEALTH` | `healthz` | `/healthz` |

**Other doc problems.**
- The [Read/Write Files docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile) say "by default the node can access any path the n8n process can reach", then note the 2.0 `~/.n8n-files` default. The page is self-contradictory.
- [Execute Command docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand): the apk-restore snippet fails on the current DHI-based image (E9). The working variant in §5 is **not** official.
- [Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker) is flagged outdated, still sets `N8N_RUNNERS_ENABLED=true`, and calls `next` "unstable".
- The [image README](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n/README.md) uses `docker.n8n.io` and links old doc paths plus `packages/cli/BREAKING-CHANGES.md`.
- [Set up task runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners) names the launcher config both `/etc/task-runners.json` and `/etc/n8n-task-runners.json`, and its example compose still uses `1.111.0` with `N8N_RUNNERS_ENABLED`.
- [n8n-base Dockerfile](https://github.com/n8n-io/n8n/blob/n8n@2.38.6/docker/images/n8n-base/Dockerfile) defaults `DHI_REF` to Node 24.19.0, while bake and the shipped image use 26.7.0. The unrelated `engine` image uses node 24.18.1.

**GitHub prerelease flags.**
- `n8n@2.38.1` is `prerelease=false` although it was a beta-track patch (not explained by the scripts).
- `n8n@2.0.0` is `false` while `2.0.1` is `true`.
- `published_at` of `n8n@2.38.0` is the re-release time.

**Re-pushed version tags.** `2.38.0` was re-published on 2026-09-08 from a second "Release 2.38.0" PR, with a new Docker digest; npm kept the 2026-09-01 artifact. The reason isn't documented, and whether image contents differ materially was not checked.

**3.x transition.** "October 2026" appears only on the docs page. No source defines how `stable`/`latest`/`releases/latest` move to 3.x (the pipeline currently rejects major bumps), whether a `v2` maintenance track will exist, or when `latest`/`next` are removed.

**Unverified or partly verified.**
- docker.n8n.io ⇔ Docker Hub mapping: auth-challenge evidence only; the digest check got HTTP 429.
- Cosign attestation identity/signature was not verified; no `.sig` exists.
- Whether the compose file embedded in "Install using Docker Compose" is exactly `docker/get-n8n-compose.yml`.
- `NODES_EXCLUDE` needing to be set on queue workers (inferred).
- Busybox `wget` exit status on HTTP 503, for a Compose healthcheck.
- `/metrics` returned HTTP 200 once on 2.38.6 during early startup; a settled 2.38.7 instance returned 404. The early 200 is unexplained.
- arm64 behaviour (all empirical checks ran on amd64).
- `2.38.7`: only config, index, 404 checks and the E9 builds were run. Deep checks E3/E6/E7 used `2.38.6`, whose docker/config sources are unchanged in 2.38.7.
