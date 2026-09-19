# n8n-custom-ytdlp

Custom [n8n](https://n8n.io/) image bundled with [yt-dlp](https://github.com/yt-dlp/yt-dlp), so workflows can download and process media directly.

## Status

The custom image can be built and tested locally and on pull requests, natively
on amd64 and arm64. A maintainer can publish through the manual workflow after
merge and approval of its first run. Failed publishing runs are reported as a
GitHub Issue. Scheduled upstream tracking comes later.

## Build and test locally

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

The image adds yt-dlp, ffmpeg and ffprobe, enables Node.js in `/etc/yt-dlp.conf`,
and creates the empty n8n files folder `/home/node/.n8n-files` owned by `node`.
It preserves upstream n8n's startup and settings. Execute Command remains
disabled by default. The generic [example Compose file](examples/compose.yaml)
is the source of the `NODES_EXCLUDE` deployment setting that enables Execute
Command while keeping only Local File Trigger excluded. Copy that setting into
your service, or adapt the example, which also persists n8n data and the n8n files
folder in named volumes.

Before the first approved publishing run, try the example with a locally built image:

```sh
docker tag n8n-ytdlp:local aliyusufergin/n8n-ytdlp:2
docker compose -f examples/compose.yaml up -d
```

Keep the JSON valid: n8n treats invalid JSON in `NODES_EXCLUDE` as an empty list,
which enables every node.

The workflow acceptance test reads that setting with `docker compose config`,
imports [a fixture workflow](tests/fixtures/media-workflow.json) using
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

## Locked build inputs

The JSON lock records n8n's version and image index digest, the matching runners
index digest, the yt-dlp nightly tag and both musllinux asset checksums, and
ffmpeg's version and multi-architecture digest. Docker selects the image for the
host architecture; the recipe selects and verifies the corresponding yt-dlp asset.
Build arguments contain only public metadata.

The seed's `published.build_tag` and `published.image_digest` are `null` until
the first successful publish fills these fields. Local builds generate a UTC
build tag for their image labels and leave the committed lock unchanged.

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

## Updater planning

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
| `reason` | `build inputs changed`, `<trigger> trigger` or `build inputs unchanged` |
| `change_summary` | What the build publishes, e.g. `yt-dlp 2026.08.30.232658 → 2026.09.16.232951`, or `n8n X.Y.Z rebuild` when no build input changed; `null` without a build |
| `new_lock` | Lock contents for the plan |
| `floating_tags` | Exactly `X`, `X.Y`, `X.Y.Z` from the planned n8n version |
| `build_tag` | `X.Y.Z-YYYYMMDD-HHMM` from the planned n8n version and the run's UTC time |
| `notices` | One-off [notices](#failure-issues-and-notices), each `{"key", "title", "body"}`; currently only the n8n 3.x notice |

The updater resolves n8n and the yt-dlp nightly from upstream; ffmpeg is still
taken from the lock and arrives in a later slice.

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

A bad signature, a missing asset or any failed request exits with status 1 and
prints no plan, so nothing is built or published. GitHub API requests send the
`GITHUB_TOKEN` environment variable when it is set, as the publishing workflow
does, and never forward it to other hosts.

Any build input that differs from the lock requests a build, whatever the
trigger. Otherwise `scheduled` skips building, while `manual`, `push` and
`pull_request` still request one. Tags are included in either case, and never
include `latest`. A `push` means a qualifying push; documentation-only filtering
belongs to the calling workflow. A plan requests only a build: pull-request
callers must never publish.

`--now` accepts an ISO 8601 timestamp with `Z` or a UTC offset and normalizes it
to UTC; omitting it uses the current UTC time. `--lock` defaults to the repository's
`build-inputs.lock.json`, regardless of the working directory. The command leaves
the file and its `published` metadata unchanged; only successful publishing can
record a new published result. Bootstrapping a missing lock arrives in a later
slice. For now a missing or unreadable lock, a nonnumeric n8n version, a version
outside major 2, or invalid command arguments exit with status 2 and a
diagnostic on stderr.

`--replay DIR` answers every upstream request from responses recorded in `DIR`
and never uses the network; a request without a recording fails the run.
`--record DIR` saves every live response there for later replay. See
[the recordings](tests/fixtures/upstream/README.md) for the file layout.

Run the offline command acceptance tests. They replay real recorded upstream
responses and control the clock. For n8n they cover a stable-track update, a
re-pushed digest, ignored prerelease flags, a Docker tag not pushed yet and a
3.x marker with and without later 2.x patches. For yt-dlp they cover a new
nightly, an unchanged nightly, a bad signature and a missing asset:

```sh
python3 tests/test_updater.py
```

## Pull-request checks

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
also supplies candidates to the manual publishing pipeline. Pull-request checks need
no repository secrets, use only `contents: read`, and disable persisted checkout
credentials. They do not log in to registries, push images, attest, commit, or
open issues. Buildx's default provenance attestations are disabled for these
checks. The checkout action is pinned to a full commit SHA.

## Manual publishing

The [Manual publish workflow](.github/workflows/publish.yml) accepts only
`workflow_dispatch` on `main`. After merge, the first run requires the maintainer's
explicit approval. A maintainer can then start it from Actions or with:

```sh
gh workflow run publish.yml --ref main
```

It calls the updater with `--trigger manual`, then reuses the native amd64 and
arm64 build-and-test jobs. Each job exports one OCI archive with BuildKit
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
have not changed since the tested revision, records the verified custom image
index digest and build tag, and pushes a commit with `GITHUB_TOKEN`. The commit
message is the plan's change summary plus the build tag, e.g.
`Publish yt-dlp 2026.08.30.232658 → 2026.09.16.232951 (2.38.7-20260919-1200)`.
It never force-pushes. A competing push can reject the commit; start a new run
after resolving the competing change. Workflow-token pushes do not retrigger CI.

Publishing runs are serialized with `cancel-in-progress: false`. A failure stops
the remaining steps and prevents the lock commit. Registry tag updates across
two repositories are not atomic: an interrupted publish may move some tags.
The next successful run republishes all tags to restore pairing. This slice
does not add schedules or push triggers.

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

After the approved first run, verify anonymously on native amd64 and arm64 hosts:

```sh
docker pull aliyusufergin/n8n-ytdlp:2
python3 tests/test_image.py aliyusufergin/n8n-ytdlp:2 build-inputs.lock.json
regctl image digest aliyusufergin/n8n-ytdlp-runners:2
```

Use the newly committed lock and pull its upstream n8n digest before running the
suite as described above. Compare the runners result with `n8n.runners_digest`
in that lock; repeat for its minor, patch and build tags. This live verification
is still pending until the first publishing run is approved.

### Sigstore attestation

Each published custom image index gets a keyless, Sigstore-backed
[GitHub artifact attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
of SLSA build provenance, created by [`actions/attest`](https://github.com/actions/attest).
There is no signing key to manage: the job obtains a short-lived Sigstore
certificate through GitHub OIDC. The certificate names this repository, the
`.github/workflows/publish.yml` workflow and `refs/heads/main`, and the signature
is recorded in Sigstore's public transparency log. The attestation covers the
index digest, so every tag of that image shares it. It is pushed to Docker Hub
beside the image and also stored by GitHub. The companion runners image is not
attested.

Verify a published custom image with [GitHub CLI](https://cli.github.com/) 2.68
or later. `gh` requires a GitHub login (`gh auth login`), even though this
command reads the attestation from Docker Hub:

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
Custom images published before attestation was added have no attestation and
fail verification too. Renaming the workflow file would likewise make the
command reject every custom image attested before the rename.

### Vulnerability report

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

## Failure issues and notices

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
