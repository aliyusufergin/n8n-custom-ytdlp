# n8n-custom-ytdlp

The custom image `aliyusufergin/n8n-ytdlp` is the official [n8n](https://n8n.io/)
2.x image with the [yt-dlp](https://github.com/yt-dlp/yt-dlp) nightly, ffmpeg and
ffprobe added, so n8n workflows can download and process media. It follows n8n's
stable track, runs on linux/amd64 and linux/arm64, and leaves n8n's own behaviour
unchanged.

A deployment adopts it by changing only the `image:` line of its Compose file.
Whether workflows may run shell commands stays each deployment's decision.

This README starts with what deployments need. [Maintaining this
repository](#maintaining-this-repository) covers how the custom image is built,
tested and published.

## Status

Custom images are published on
[Docker Hub](https://hub.docker.com/r/aliyusufergin/n8n-ytdlp). A scheduled
workflow checks n8n, yt-dlp and ffmpeg every 6 hours and publishes a new custom
image when any of them changed, so updates usually arrive within hours.

## What the custom image adds

The custom image is the upstream n8n image of n8n's stable track, plus:

- **The yt-dlp nightly** as `yt-dlp` on the `PATH`. It is yt-dlp's single-file
  musllinux build, which bundles Python and yt-dlp's optional modules: browser
  impersonation (curl_cffi), websockets, brotli, encrypted HLS (pycryptodomex),
  metadata and thumbnail embedding (mutagen), and yt-dlp-ejs for YouTube's
  JavaScript challenges. The build checks the binary against yt-dlp's signed
  checksum list.
- **ffmpeg and ffprobe** on the `PATH`, static builds from
  [`mwader/static-ffmpeg`](https://github.com/wader/static-ffmpeg). yt-dlp uses
  them to merge separate video and audio, convert audio and embed metadata.
- **`/etc/yt-dlp.conf`** with a single option, `--js-runtimes node`. yt-dlp then
  solves YouTube's JavaScript challenges with the Node.js that n8n already ships,
  without extra flags.
- **The n8n files folder** `/home/node/.n8n-files`, empty and owned by `node`.
- **Labels** that record every build input and the build tag; see
  [Verify a custom image](#verify-a-custom-image).

The tools are owned by root and run as `node`, n8n's user, from the Execute
Command node.

## What it leaves out, and why

- **Execute Command stays disabled.** The custom image doesn't set
  `NODES_EXCLUDE`, so n8n 2.x's default still excludes the Execute Command node.
  Pulling an image must never loosen n8n's security defaults for everyone who
  uses it, so enabling shell access is a deployment setting
  ([ADR 0001](docs/adr/0001-execute-command-enabled-by-deployments.md)). See
  [Enable Execute Command](#enable-execute-command).
- **n8n's container contract is unchanged.** The user `node`, working directory,
  entrypoint, command, exposed port and environment match the upstream n8n image.
  No `VOLUME` or `HEALTHCHECK` is added. Existing data, encryption keys,
  databases and credentials keep working.
- **No package manager and no extra runtime.** The upstream n8n image ships
  without a package manager, and the custom image doesn't restore one or add
  Python, Deno or glibc. yt-dlp brings its own Python, ffmpeg is static and
  yt-dlp uses n8n's Node.js, so none of them is needed.
- **No yt-dlp defaults besides the JavaScript runtime.** Formats, output
  templates and every other option stay each workflow's decision.
- **No other tools.** No `ffplay`, PO token providers, AtomicParsley, aria2c,
  PhantomJS or rtmpdump. yt-dlp treats all of them as optional.
- **Only n8n's stable track, major version 2.** No n8n betas or 3.x, no
  rebuilds of older 2.x versions, and no `-pc` variants, which n8n reserves for
  n8n Cloud.
- **The companion runners image is not modified.**
  `aliyusufergin/n8n-ytdlp-runners` is an unmodified copy of `n8nio/runners`,
  without yt-dlp or ffmpeg. See external task runners in the
  [deployment checklist](#deployment-checklist).

## Use the custom image

Change only the image of the n8n service:

```yaml
services:
  n8n:
    image: aliyusufergin/n8n-ytdlp:2
```

- Keep the existing volumes and environment. n8n's data folder, encryption key,
  database and credentials keep working.
- Pull anonymously; no registry login or token is needed.
- The same tag works on amd64 and arm64 hosts.
- Choose the tag in [Tags](#tags). Its n8n version should not be older than the
  one the deployment runs now: a database that a newer n8n has migrated may not
  work with an older one.

The generic [example Compose file](examples/compose.yaml) shows a complete n8n
service with the custom image, the Execute Command setting, and named volumes for
n8n's data and the n8n files folder. It contains no host-specific values; adapt it
to your deployment.

### Enable Execute Command

Workflows run yt-dlp, ffmpeg and ffprobe through n8n's Execute Command node,
which n8n 2.x excludes by default. Enable it in the deployment's Compose file with
this exact setting from the [example Compose file](examples/compose.yaml):

```yaml
services:
  n8n:
    environment:
      NODES_EXCLUDE: '["n8n-nodes-base.localFileTrigger"]'
```

The value replaces n8n's default list,
`["n8n-nodes-base.executeCommand","n8n-nodes-base.localFileTrigger"]`. Execute
Command becomes available and Local File Trigger stays excluded. The image tests
run their workflow with this value.

> [!WARNING]
> n8n reads invalid JSON in `NODES_EXCLUDE` as an empty list, which **enables
> every node**, Local File Trigger included. Keep the single quotes so that YAML
> passes the JSON through unchanged, and check the value n8n receives:
>
> ```sh
> docker compose exec n8n node -e 'console.log(JSON.parse(process.env.NODES_EXCLUDE))'
> ```
>
> It prints `[ 'n8n-nodes-base.localFileTrigger' ]`, or fails with a
> `SyntaxError` when the JSON is invalid.

Execute Command runs any shell command as `node` inside the n8n container. The
command sees the container's environment variables, such as `N8N_ENCRYPTION_KEY`
or database passwords when they are set there. Everyone who can edit workflows
can use it, so decide who may.

### Deployment checklist

- [ ] **Execute Command:** set `NODES_EXCLUDE` as
  [shown above](#enable-execute-command) on every n8n container that runs
  workflows.
- [ ] **Upgrading from n8n 1.x:** 2.x is a major upgrade with breaking changes.
  Read n8n's [2.0 breaking changes](https://docs.n8n.io/changelog/v20-breaking-changes)
  and back up n8n's data folder and database before n8n 2.x first starts.
- [ ] **Queue mode:** run the main instance and every worker with the same
  custom image tag and the same `NODES_EXCLUDE`. Workers run workflow
  executions, so Execute Command runs yt-dlp there. Manual executions stay on the
  main instance unless `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS` is `true`
  ([Execute Command docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand)).
  Files that a command writes stay in the container that ran it.
- [ ] **External task runners:** with `N8N_RUNNERS_MODE=external`, run the
  companion runners image `aliyusufergin/n8n-ytdlp-runners` under the same tag
  as the custom image. n8n requires the runners version to match its own
  ([task runner docs](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners)),
  and both images carry the same tags. Code nodes run in the runners container
  and find no yt-dlp or ffmpeg there. Execute Command runs in the n8n container,
  which has them.
- [ ] **Volumes:** keep n8n's data folder `/home/node/.n8n` on its existing
  volume; it holds the encryption key and, by default, the SQLite database and
  binary data. Mount a volume on the n8n files folder `/home/node/.n8n-files` to
  keep downloads when the container is recreated. Read/Write Files from Disk may
  only access this folder by default, so let commands write there. A fresh named
  volume starts owned by `node`; a bind mount must be writable by UID 1000.
- [ ] **Temporary directory:** yt-dlp's single-file build unpacks itself into the
  temporary directory on every run: `$TMPDIR`, or `/tmp` when that is unset. The
  directory must be writable by `node` and allow executing files. The image's own
  `/tmp` works. With a read-only root filesystem (`read_only: true`) or a
  `noexec` `/tmp`, mount an executable tmpfs, because Docker mounts tmpfs
  `noexec` unless told otherwise:

  ```yaml
  services:
    n8n:
      tmpfs:
        - /tmp:exec
  ```

  Otherwise yt-dlp fails with `[PYI-1:ERROR] Could not create temporary
  directory!` when the directory isn't writable, or `Error loading shared library
  libz.so.1: Operation not permitted` when it isn't executable. To keep `/tmp`
  `noexec`, point `TMPDIR` at another writable, executable directory.
- [ ] **Updates and rollback:** the floating tag `2` changes almost daily, and
  n8n's database migrations can make a rollback impossible. Back up and
  [choose a tag](#choosing-a-tag) that matches your risk tolerance.

## Tags

The custom image `aliyusufergin/n8n-ytdlp` and the companion runners image
`aliyusufergin/n8n-ytdlp-runners` carry the same tags. Each tag names one image
for both linux/amd64 and linux/arm64.

| Tag | Example | Points to |
| --- | --- | --- |
| `2` | `2` | The newest custom image; its n8n version follows the stable track while that is 2.x |
| `2.Y` | `2.38` | The newest custom image of that n8n minor |
| `2.Y.Z` | `2.38.7` | The newest custom image of that n8n version |
| `2.Y.Z-YYYYMMDD-HHMM` | `2.38.7-20260919-1300` | Exactly one custom image, built at that UTC minute |

- **Floating tags** (`2`, `2.Y`, `2.Y.Z`) move to each new custom image. A new
  one is published when any build input changes: a new n8n version on the stable
  track, a new yt-dlp nightly, a new ffmpeg release, or an upstream image
  re-pushed under the same version. A change to how this repository builds the
  image publishes one too. Floating tags move only after the new image passed
  every blocking test on both architectures.
- **Build tags** (`2.Y.Z-YYYYMMDD-HHMM`) never move, and Docker Hub refuses to
  overwrite them. Use one to pin a known-good image or to roll back.
- **There is no `latest` tag.** An image reference without a tag fails to pull,
  so nobody follows a line by accident.
- **Only the current stable-track version is rebuilt.** When n8n's stable track
  moves on, for example from 2.38.7 to 2.38.8 or to 2.39, older floating tags
  such as `2.38.7` and `2.38` stay on their last custom image and get no newer
  yt-dlp or ffmpeg. n8n's stable track usually moves to a new minor every week.
- **No n8n betas, no 3.x.** No tag contains an n8n beta, and `2` never moves to
  n8n 3.x. When n8n marks a 3.x release as its latest, the custom image keeps
  following patches of its current 2.x minor while n8n publishes them, then stays
  on the last one. Its floating tags still receive new yt-dlp and ffmpeg builds;
  only the n8n version stops moving.

### Choosing a tag

| Tag | n8n version | New yt-dlp and ffmpeg builds |
| --- | --- | --- |
| `2` | Follows the stable track while it is 2.x, then stays on the last 2.x version | Always |
| `2.Y` | Patches of one minor | Until the custom image moves to the next n8n minor, usually within about a week |
| `2.Y.Z` | Fixed | Until the custom image moves to the next n8n patch, often within days |
| Build tag | Fixed | Never |

Old yt-dlp builds stop working on YouTube quickly. A tag that no longer receives
updates freezes yt-dlp too, so pinning `2.Y`, `2.Y.Z` or a build tag trades
working YouTube downloads for a fixed n8n version.

Automatic updaters such as Watchtower or Dockhand check the floating tag on their
own schedule and recreate the container each time it has moved.

> [!WARNING]
> The floating tag `2` changes almost daily: n8n publishes stable-track patches
> almost daily, and yt-dlp publishes several nightlies a week. n8n migrates its
> database when a new version first starts, and a migrated database may not work
> with the previous version, so rolling back can be impossible. Back up n8n's data
> folder and database regularly, and before updates where you can. Choose the tag
> that matches your risk tolerance.

To roll back, pin the build tag the deployment ran before and restore the backup
taken before the update. Note the build tag of a running container with:

```sh
docker inspect --format '{{index .Config.Labels "org.opencontainers.image.version"}}' <container>
```

Each publishing commit in this repository's history names its build tag too.

## Verify a custom image

### Sigstore attestation

Each published custom image index gets a keyless, Sigstore-backed
[GitHub artifact attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
of SLSA build provenance, created by [`actions/attest`](https://github.com/actions/attest).
There is no signing key to manage: the publishing workflow obtains a short-lived
Sigstore certificate through GitHub OIDC. The certificate names this repository, the
`.github/workflows/publish.yml` workflow and `refs/heads/main`, and the signature
is recorded in Sigstore's public transparency log. The attestation covers the
index digest, so every tag of that image shares it. It is pushed to Docker Hub
beside the image and also stored by GitHub. The companion runners image is not
attested.

Verify a published custom image with [GitHub CLI](https://cli.github.com/) 2.97
or later. Versions 2.68 to 2.96 run the command too, but match `--signer-workflow`
as an unescaped pattern, so a lookalike workflow name could pass
([GHSA-mm27-mwq9-fr5g](https://github.com/cli/cli/security/advisories/GHSA-mm27-mwq9-fr5g)).
`gh` requires a GitHub login (`gh auth login`), even though this command reads
the attestation from Docker Hub:

```sh
gh attestation verify oci://docker.io/aliyusufergin/n8n-ytdlp:2 \
  --repo aliyusufergin/n8n-custom-ytdlp \
  --signer-workflow aliyusufergin/n8n-custom-ytdlp/.github/workflows/publish.yml \
  --source-ref refs/heads/main \
  --bundle-from-oci
```

Any tag works in place of `2`. The command resolves the tag to its digest, then
checks the Sigstore signature, the transparency log entry and the certificate's
workflow identity. It exits with status 0 only when an attestation from this
workflow on `main` covers exactly that digest. Without `--bundle-from-oci`, it
fetches the attestation from GitHub instead of Docker Hub.

The same command fails for any image this workflow did not build. For example,
with `oci://docker.io/n8nio/n8n:2.38.7` it exits with status 1 and reports
`no attestations found in the OCI registry`. After attesting, every publishing run
executes both cases: the new build tag must pass, and the locked upstream n8n
image must fail. The run summary shows why the upstream n8n image was rejected.
Custom images published before attestation was added, the build tags
`2.38.7-20260913-1644` and `2.38.7-20260919-1203`, have no attestation and fail
verification too. Renaming the workflow file would likewise make the
command reject every custom image attested before the rename.

### Build inputs, provenance and SBOM

Every custom image records its build inputs in labels:

```sh
docker image inspect --format '{{json .Config.Labels}}' aliyusufergin/n8n-ytdlp:2
```

The `io.github.aliyusufergin.n8n-ytdlp.*` labels name the build tag, the n8n
version and upstream n8n image digest, the companion runners image digest, the
yt-dlp nightly tag and checksums, and the ffmpeg version and digest. The standard
`org.opencontainers.image.*` labels add the source repository, revision, creation
time and version, which is the build tag.

Each platform image also carries BuildKit provenance and an SBOM:

```sh
docker buildx imagetools inspect aliyusufergin/n8n-ytdlp:2 --format '{{json .Provenance}}'
docker buildx imagetools inspect aliyusufergin/n8n-ytdlp:2 --format '{{json .SBOM}}'
```

Each publishing run adds a [vulnerability report](#vulnerability-report) to its
run summary in
[GitHub Actions](https://github.com/aliyusufergin/n8n-custom-ytdlp/actions/workflows/publish.yml).
Findings never block publishing.

## yt-dlp updates

yt-dlp updates arrive in newer custom images, not through yt-dlp's self-update.
Each new yt-dlp nightly produces a new custom image under the current floating
tags, so pulling the deployment's tag again, for example with
`docker compose pull && docker compose up -d`, brings the newest yt-dlp.

Don't update yt-dlp inside a container. The binary is owned by root, so
`yt-dlp -U` running as `node` cannot replace it and fails with
`ERROR: Insufficient permissions to write to /usr/local/bin/yt-dlp`. Any change
inside a container is lost when the container is recreated anyway.

If YouTube downloads start failing, check that the deployment's tag still
receives updates; see [Choosing a tag](#choosing-a-tag).

## Licenses

These notes summarize the licenses of the software that the custom image
redistributes. They are not legal advice; the linked license texts apply.

- **n8n**, in the custom image and in the companion runners image, is under
  n8n's [Sustainable Use License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md).
  Files with `.ee.` in their name or `.ee` in their directory name need an n8n
  Enterprise License instead. The Sustainable Use License says: "You may use or
  modify the software only for your own internal business purposes or for
  non-commercial or personal use. You may distribute the software or provide it
  to others only if you do so free of charge for non-commercial purposes." The
  custom image is published free of charge, and these terms apply to every
  deployment that runs it.
- **yt-dlp** is under the [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE).
  Its single-file builds, which the custom image uses, include GPLv3+ licensed
  code, so yt-dlp licenses each such binary as a whole under
  [GPLv3+](https://www.gnu.org/licenses/gpl-3.0.html). See yt-dlp's
  [licensing notes](https://github.com/yt-dlp/yt-dlp#licensing) and
  [third-party licenses](https://github.com/yt-dlp/yt-dlp/blob/master/THIRD_PARTY_LICENSES.txt).
  Each [nightly release](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases)
  names the yt-dlp commit it was built from; the image's `yt-dlp.tag` label names
  the release.
- **ffmpeg and ffprobe** from [`mwader/static-ffmpeg`](https://github.com/wader/static-ffmpeg)
  are built with `--enable-gpl --enable-version3`, so they are licensed under the
  GNU GPL version 3 or later; `ffmpeg -L` prints the notice. They statically link
  third-party libraries under their own licenses, which that project's build
  recipe lists. See FFmpeg's [license and legal notes](https://www.ffmpeg.org/legal.html).
  The image's `ffmpeg.version` label names the FFmpeg release, whose source is
  available from [ffmpeg.org](https://ffmpeg.org/download.html).

## Maintaining this repository

The rest of this README is for maintainers: how the custom image is built,
tested and published.

### Build and test locally

Requires Python 3.10+ and Docker with Buildx, Compose v2+ and a running Linux Docker daemon.
From this checkout, run:

```sh
python3 scripts/build_and_test.py
```

This builds `n8n-ytdlp:local` for the Docker host's architecture (amd64 or arm64)
from [build-inputs.lock.json](build-inputs.lock.json), then runs the Python standard
library image acceptance suite. The build needs network access to Docker Hub and
the pinned GitHub release. Blocking image tests run without external network access;
the advisory YouTube test uses the network and reports failures as warnings.
Readiness is probed over HTTP inside a temporary container, without publishing
a host port. Test containers and named volumes are removed after use.

The suite compares the custom image's user, working directory, entrypoint,
command, exposed ports and environment with the locked upstream n8n image.
It checks that Execute Command is unavailable with default settings, that
yt-dlp running as `node` detects the image's Node.js, ffmpeg and ffprobe, and
that `node` can write to a fresh named volume at `/home/node/.n8n-files`.

To test an already loaded candidate, or run one test while developing:

```sh
python3 tests/test_image.py n8n-ytdlp:local build-inputs.lock.json
python3 scripts/build_and_test.py ImageTests.test_yt_dlp_version
```

Both commands accept a candidate image and lock file: the build command uses
`--image` and `--lock`, while the suite takes them as positional arguments.
The suite also needs the locked upstream n8n image locally to compare the
container contract; the build command pulls it, or pull it by its locked digest
before testing a separately supplied candidate.

To try the [example Compose file](examples/compose.yaml) with a locally built
custom image, tag it under the example's image name:

```sh
docker tag n8n-ytdlp:local aliyusufergin/n8n-ytdlp:2
docker compose -f examples/compose.yaml up -d
```

The example Compose file is the source of the `NODES_EXCLUDE` deployment setting.
The workflow acceptance test reads that setting with `docker compose config`,
checks that [Enable Execute Command](#enable-execute-command) shows the same
line, imports [a fixture workflow](tests/fixtures/media-workflow.json) using
`import:workflow`, and runs it with `execute --id`. Its Execute Command node runs
yt-dlp and ffmpeg as `node`, generates audio in the n8n files folder, and passes
it to Read/Write Files from Disk. The test checks the successful execution and
binary output. A separate offline test generates video and audio, merges and
converts them, then checks the streams, codecs and duration with ffprobe.

The YouTube test attempts to download "Me at the zoo" using
`worstvideo+worstaudio`, merges the separate streams with ffmpeg and checks the
result with ffprobe. It has a 180-second timeout; all failures are non-blocking
warnings. To reproduce a real network failure without waiting for a bot check:

```sh
python3 scripts/build_and_test.py --youtube-network none ImageTests.test_youtube_download
```

The already-loaded-image command accepts `--youtube-network none` too. This
only disables the YouTube test container's network; blocking tests always run
without external network access.

### Locked build inputs

The JSON lock records n8n's version and image index digest, the matching runners
index digest, the yt-dlp nightly tag and both musllinux asset checksums, and
ffmpeg's version and multi-architecture digest. Docker selects the image for the
host architecture; the recipe selects and verifies the corresponding yt-dlp asset.
Build arguments contain only public metadata.

`published.build_tag` and `published.image_digest` record the last successful
publish; they were `null` in the seed. Local builds generate a UTC build tag for
their image labels and leave the committed lock unchanged.

The seed was resolved from upstream on 2026-09-12:

- n8n `2.38.7` came from the GitHub
  [stable-track marker](https://api.github.com/repos/n8n-io/n8n/releases/latest).
  The n8n and runners index digests were resolved for that exact version.
- yt-dlp nightly `2026.08.30.232658` came from its GitHub
  [release marker](https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases/latest).
  Its [SHA2-256SUMS and detached signature](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/tag/2026.08.30.232658)
  were downloaded and verified with GPG in an isolated keyring. `VALIDSIG` matched
  the pinned fingerprint `AC0CBBE6848D6A873464AF4E57CF65933B5A7581`; both asset
  checksums were taken from that verified list.
- ffmpeg `9.0.1` was the highest numeric `X.Y.Z` tag in the complete
  [Docker Hub tag list](https://hub.docker.com/v2/repositories/mwader/static-ffmpeg/tags?page_size=100).
  Its multi-architecture digest was resolved from the registry.

All three upstream image indexes were checked to include linux/amd64 and
linux/arm64.

### Updater planning

Run the planner locally or in CI with Python 3, its standard library and `gpgv`
(GnuPG's signature verifier):

```sh
python3 scripts/updater.py --trigger scheduled
python3 scripts/updater.py --lock build-inputs.lock.json --trigger manual --now 2026-09-12T06:17:00Z
```

The command prints one JSON object to stdout with these fields:

| Field | Meaning |
| --- | --- |
| `build` | Whether this run should build |
| `reason` | `build inputs changed`, `no lock file`, `<trigger> trigger` or `build inputs unchanged` |
| `change_summary` | What the build publishes, e.g. `yt-dlp 2026.08.30.232658 → 2026.09.16.232951`, every build input without a lock file, or `n8n X.Y.Z rebuild` when no build input changed; `null` without a build |
| `new_lock` | Lock contents for the plan |
| `floating_tags` | Exactly `X`, `X.Y`, `X.Y.Z` from the planned n8n version |
| `build_tag` | `X.Y.Z-YYYYMMDD-HHMM` from the planned n8n version and the run's UTC time |
| `notices` | One-off [notices](#failure-issues-and-notices), each `{"key", "title", "body"}`; currently only the n8n 3.x notice |

The updater resolves every build input from upstream: n8n, the yt-dlp nightly
and ffmpeg.

For n8n it follows the stable track
([ADR 0002](docs/adr/0002-n8n-version-from-latest-release-marker.md)):

1. reads `releases/latest` of `n8n-io/n8n`; an `n8n@2.Y.Z` marker is the planned
   version. GitHub prerelease flags are ignored, because n8n's are unreliable;
2. when the marker's major version is not 2, plans the highest `n8n@2.Y.Z` tag
   on the locked `2.Y` minor, or keeps the locked version when none is newer. n8n
   creates each such tag with its release, and one request lists a minor's tags.
   It also raises the notice `n8n-<major>` ("n8n 3.x available"), which opens
   one issue per major version;
3. resolves the `n8nio/n8n` and `n8nio/runners` index digests of the planned
   version with anonymous Docker Hub manifest HEAD requests, which don't count
   against pull limits.

A changed digest under the same version plans a build (`n8n X.Y.Z republished`).
When either Docker tag of a newly planned version is not pushed yet, the run keeps
the locked n8n entry, says so on stderr and does not fail; a later run retries.
A missing Docker tag of the locked version itself fails the run.

For yt-dlp it:

1. reads `releases/latest` of `yt-dlp/yt-dlp-nightly-builds`;
2. downloads that release's `SHA2-256SUMS` and `SHA2-256SUMS.sig`;
3. verifies the signature with `gpgv` against
   [yt-dlp's signing key](scripts/yt-dlp-signing-key.asc), committed from
   yt-dlp's `public.key` and pinned to fingerprint
   `AC0C BBE6 848D 6A87 3464 AF4E 57CF 6593 3B5A 7581`; no key is fetched at run time;
4. records the nightly tag and the checksums of `yt-dlp_musllinux` and
   `yt-dlp_musllinux_aarch64` from that verified list.

For ffmpeg it:

1. lists the tags of `mwader/static-ffmpeg` from the Docker Hub registry and
   picks the highest release tag, compared numerically, including a new major
   version. FFmpeg names a line's first release `X.Y` and its patches `X.Y.Z`, so
   `10.0` is followed as soon as it is published and `10.0.1` replaces it later.
   The image tests gate a new major like any other version. Tags that name no
   release of their own, such as `latest`, `7.0-2` or `9.0.1-arm64`, are ignored;
2. resolves that tag's index digest with an anonymous manifest HEAD request;
3. when the digest differs from the locked one, fetches that index by digest,
   checks that it hashes to the digest and requires linux/amd64 and linux/arm64
   images in it. This fetch counts against Docker Hub's pull limit, so it
   happens only for a new digest; an unchanged digest names the index that was
   already checked.

A new version (`ffmpeg 9.0.1 → 9.1`) or a changed digest under the same
version (`ffmpeg 9.0.1 republished`) plans a build.

A bad signature, a missing asset, an ffmpeg index without both platforms or any
failed request exits with status 1 and prints no plan, so nothing is built or
published. GitHub API requests send the
`GITHUB_TOKEN` environment variable when it is set, as the publishing workflow
does, and never forward it to other hosts.

Any build input that differs from the lock requests a build, whatever the
trigger. Otherwise `scheduled` skips building, while `manual`, `push` and
`pull_request` still request one. Tags are included in either case, and never
include `latest`. A `push` means a qualifying push; documentation-only filtering
belongs to the [calling workflow](#publishing). A plan requests only a build:
pull-request callers must never publish.

`--now` accepts an ISO 8601 timestamp with `Z` or a UTC offset and normalizes it
to UTC; omitting it uses the current UTC time. `--lock` defaults to the repository's
`build-inputs.lock.json`, regardless of the working directory. The command leaves
the file and its `published` metadata unchanged; only successful publishing can
record a new published result.

A missing lock file counts as every build input changed. The plan resolves all
of them and requests a build for any trigger, with the reason `no lock file` and
a summary such as `n8n 2.38.7, yt-dlp 2026.09.16.232951, ffmpeg 9.0.1`. Without a
lock there is no n8n version to keep and no 2.x minor to follow, so a Docker tag
that is not pushed yet or an n8n 3.x marker fails the run instead.

An unreadable lock, a nonnumeric n8n version, a version outside major 2, or
invalid command arguments exit with status 2 and a diagnostic on stderr.

`--replay DIR` answers every upstream request from responses recorded in `DIR`
and never uses the network; a request without a recording fails the run.
`--record DIR` saves every live response there for later replay. See
[the recordings](tests/fixtures/upstream/README.md) for the file layout.

Run the offline command acceptance tests. They replay real recorded upstream
responses and control the clock. For n8n they cover a stable-track update, a
re-pushed digest, ignored prerelease flags, a Docker tag not pushed yet and a
3.x marker with and without later 2.x patches. For yt-dlp they cover a new
nightly, an unchanged nightly, a bad signature and a missing asset. For ffmpeg
they cover a new version, a new major version from its first `X.Y` release,
ignored non-release tags, a re-pushed digest, an index missing a platform or not
matching its digest, and a listed tag without an index. Without a lock file they
cover a full plan, an n8n 3.x marker and a Docker tag not pushed yet:

```sh
python3 tests/test_updater.py
```

### Pull-request checks

Every pull request also runs the offline updater command suite in a separate job.

Every pull request runs `python3 scripts/build_and_test.py` on native
`ubuntu-24.04` (amd64) and `ubuntu-24.04-arm` (arm64) GitHub-hosted runners,
without QEMU. Each job builds its own custom image from the committed lock file
and runs the same acceptance suite as the local command. Both architectures
finish even if one fails; a blocking test failure fails its job.

Each job copies the final 60 KB of build and test output, including suite
warnings, into the run summary even when a test fails. The full output remains
in the job log. Warning-only tests must report their warning and return success
so they do not mask blocking failures or fail the job themselves.
After the normal suite, each job repeats just the YouTube test with networking
disabled. This verifies that an actual download failure emits the warning and
returns success. That output and the verification outcome also appear in the
run summary, independently of whether the live YouTube request succeeds.

The [Image workflow](.github/workflows/image.yml) calls the
[reusable build-and-test workflow](.github/workflows/build-and-test.yml), which
also supplies candidates to the [publishing workflow](#publishing). Pull-request checks need
no repository secrets, use only `contents: read`, and disable persisted checkout
credentials. They do not log in to registries, push images, attest, commit, or
open issues. Buildx's default provenance attestations are disabled for these
checks. The checkout action is pinned to a full commit SHA.

### Publishing

The [Publish workflow](.github/workflows/publish.yml) publishes from `main` only.
It starts:

- **Every 6 hours at minute 17** UTC. It publishes only when the plan says a
  build input changed.
- **On a push to `main`** that changes more than documentation. It publishes even
  when no build input changed, so changes to the image recipe or the pipeline
  reach the image. A push that changes only Markdown files, `docs/` or
  `examples/` does not start it, so a README fix does not restart
  auto-updating deployments. Merging a pull request is such a push.
- **By hand**, from Actions or with the command below. Like a push, it publishes
  even when no build input changed.

```sh
gh workflow run publish.yml --ref main
```

A separate monthly schedule only
[re-enables the workflow](#re-enable-the-scheduled-workflow).

One run is active at a time. Later runs wait in order and never cancel a running
one (`cancel-in-progress: false` with `queue: max`). Each run plans against the
lock file on `main` when it starts, not the lock of the revision it was started
for. A run that waited behind a publishing run therefore does not publish the
same build inputs again. When `main` has no lock file, the run resolves every
build input and publishes; see [updater planning](#updater-planning).

It calls the updater with `--trigger scheduled`, `push` or `manual`, then reuses
the native amd64 and arm64 build-and-test jobs. Each job exports one OCI archive with BuildKit
provenance and an SBOM, loads it into Docker's containerd image store, verifies
that the loaded platform manifest digest matches the archive, and runs the image
suite with the plan's exact build tag. Only successful jobs upload candidates.
The publishing job checks the archives against their test receipts and the
attestation subjects, copies them without rebuilding, and creates a combined OCI
image index. It reads the manifests back to verify their digests before tagging.
The attesting job then signs that index and pushes its
[Sigstore attestation](#sigstore-attestation) to Docker Hub, and a separate job
runs the README verification command. Two further native jobs anonymously pull
the published floating tag, run the image suite on amd64 and arm64, and check all
custom and runners tag digests. The lock commit waits for the Sigstore
attestation, its verification and both native jobs to pass. Two report-only jobs
add a [vulnerability report](#vulnerability-report) to the run summary.

Both `aliyusufergin/n8n-ytdlp` and `aliyusufergin/n8n-ytdlp-runners` receive the
plan's `X`, `X.Y`, `X.Y.Z` floating tags and `X.Y.Z-YYYYMMDD-HHMM` build tag.
There is no `latest` tag. The companion runners image is copied recursively from
the locked upstream digest, with no modifications or additional attestations;
every runners tag is checked against that digest. Docker Hub's configured
immutability rule protects build tags. Use a new run with a new UTC-minute build
tag after a partial publish instead of rerunning the same plan.

Only the publishing and attesting jobs receive `DOCKERHUB_TOKEN`, using the
repository variable `DOCKERHUB_USERNAME=aliyusufergin`. Only the attesting job
has `id-token: write` and `attestations: write`. Only the final lock-commit job has
`contents: write`. It starts from current `main`, verifies that its build inputs
have not changed since planning, records the verified custom image
index digest and build tag, and pushes a commit with `GITHUB_TOKEN`. The commit
message is the plan's change summary plus the build tag, e.g.
`Publish yt-dlp 2026.08.30.232658 → 2026.09.16.232951 (2.38.7-20260919-1200)`.
It never force-pushes. A competing push can reject the commit; start a new run
after resolving the competing change. Pushes made with the workflow token start
no workflow runs, so a lock commit never starts another publishing run.

A failure stops the remaining steps and prevents the lock commit. Registry tag
updates across two repositories are not atomic: an interrupted publish may move
some tags. The next successful run republishes all tags to restore pairing.

For a local reproduction of the publishing candidate (Docker 29.8+ with the
containerd image store and Buildx with OCI export support):

```sh
python3 scripts/updater.py --trigger manual > /tmp/plan.json
python3 scripts/build_and_test.py --plan /tmp/plan.json --archive /tmp/candidate/image.tar
```

The plan's lock is written beside the plan as `candidate.lock.json`; the successful
test receipt is written beside the archive as `image.json`. Neither command
publishes or changes the repository lock. Standard local and PR builds retain
their existing behavior.

The two native verification jobs repeat this check after every publish. To repeat
it by hand, verify anonymously on native amd64 and arm64 hosts:

```sh
docker pull aliyusufergin/n8n-ytdlp:2
python3 tests/test_image.py aliyusufergin/n8n-ytdlp:2 build-inputs.lock.json
regctl image digest aliyusufergin/n8n-ytdlp-runners:2
```

Use the newly committed lock and pull its upstream n8n digest before running the
suite as described above. Compare the runners result with `n8n.runners_digest`
in that lock; repeat for its minor, patch and build tags.

#### Vulnerability report

Two report-only jobs scan the published custom image index by digest with
[Grype](https://github.com/anchore/grype) through
[`anchore/scan-action`](https://github.com/anchore/scan-action). They run on the
native amd64 and arm64 runners, so each scans its own platform's image. The action
is pinned to a full commit SHA, and the workflow pins Grype's version.
[`scripts/vulnerability_report.py`](scripts/vulnerability_report.py) turns Grype's
JSON output into the run summary: the scanned manifest, the finding counts by
severity and a table of every finding, sorted by severity and then Grype's risk
score.

Findings never fail the run: `fail-build` is off, the scan step and both jobs
continue on error, and neither the lock commit nor the failure issue waits for
them. If the scan itself fails, the summary says so. The action's warning
annotation about the severity cutoff is informational.

### Failure issues and notices

The publishing workflow's last job reports every finished run on `main` through
GitHub Issues. It is the only job with `issues: write`, and it calls
[`scripts/notify.py`](scripts/notify.py), which uses the gh CLI with the workflow
token. Pull-request runs, runs on other branches and cancelled runs never open,
comment on or close issues.

- A run with a failed or timed-out job opens an issue labelled `updater-failure`
  that links to the run and names the failed jobs.
- While that issue is open, each later failed run comments on it with its run
  link instead of opening another issue.
- The next successful run, whether or not it published, comments on the issue
  and closes it.

A notice in the plan opens an issue labelled `updater-notice` at most once per
notice key, even if an earlier issue for that key was closed. The issue body
carries the key in a hidden marker, so removing the label from a notice issue or
the marker from its body lets that notice be raised again. Notices are raised
whenever planning succeeded, even if a later job failed. The n8n 3.x notice
uses this mechanism.

The workflow creates both labels when it first needs them. They belong to the
updater and are not triage labels.

### Re-enable the scheduled workflow

GitHub disables scheduled workflows in a public repository after 60 days without
repository activity. It does not say whether the workflow's own lock commits
count. On the 1st of every month at 04:43 UTC, the Publish workflow therefore
runs one job that only marks the workflow enabled through the GitHub API. That
job has only `actions: write`, and the run builds, publishes and reports nothing.

If GitHub disabled the workflow anyway, the workflow's page in Actions shows a
banner and no new runs appear. A disabled workflow runs for no trigger, not even
a push. Re-enable it with **Enable workflow** on that page, or with:

```sh
gh workflow enable publish.yml
```

The next scheduled run then publishes whatever changed while the workflow was
disabled. A manual run publishes at once, but it always builds, even when nothing
changed. GitHub sends notifications about failed scheduled runs to whoever last
re-enabled the workflow or changed its schedule.
