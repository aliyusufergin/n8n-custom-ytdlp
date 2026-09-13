# n8n-custom-ytdlp

Custom [n8n](https://n8n.io/) image bundled with [yt-dlp](https://github.com/yt-dlp/yt-dlp), so workflows can download and process media directly.

## Status

The custom image can be built and tested locally and on pull requests, natively
on amd64 and arm64. A maintainer can publish through the manual workflow after
merge and approval of its first run. Scheduled upstream tracking comes later.

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

Run the planner locally or in CI with Python 3 and the standard library:

```sh
python3 scripts/updater.py --trigger scheduled
python3 scripts/updater.py --lock build-inputs.lock.json --trigger manual --now 2026-09-12T06:17:00Z
```

The command prints one JSON object to stdout with these fields:

| Field | Meaning |
| --- | --- |
| `build` | Whether this run should build |
| `reason` | `build inputs unchanged` or `<trigger> trigger` |
| `new_lock` | Lock contents for the plan |
| `floating_tags` | Exactly `X`, `X.Y`, `X.Y.Z` from the locked n8n version |
| `build_tag` | `X.Y.Z-YYYYMMDD-HHMM` from the run's UTC time |
| `notices` | Notices to raise; currently an empty list |

This first slice takes the lock's build inputs as the current state and makes
no network requests. `scheduled` therefore skips building; `manual`, `push`
and `pull_request` request a build even with unchanged inputs. Tags are included
in either case, and never include `latest`. A `push` means a qualifying push;
documentation-only filtering belongs to the calling workflow. A plan requests
only a build: pull-request callers must never publish.

`--now` accepts an ISO 8601 timestamp with `Z` or a UTC offset and normalizes it
to UTC; omitting it uses the current UTC time. `--lock` defaults to the repository's
`build-inputs.lock.json`, regardless of the working directory. The command leaves
the file and its `published` metadata unchanged; only successful publishing can
record a new published result. Upstream resolution and bootstrapping a missing
lock arrive in later slices. For now a missing or unreadable lock, a nonnumeric
n8n version, a version outside major 2, or invalid command arguments fail with a
nonzero exit code and a diagnostic on stderr.

Run the offline command acceptance tests (including controlled-clock cases):

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

Both `aliyusufergin/n8n-ytdlp` and `aliyusufergin/n8n-ytdlp-runners` receive the
plan's `X`, `X.Y`, `X.Y.Z` floating tags and `X.Y.Z-YYYYMMDD-HHMM` build tag.
There is no `latest` tag. The companion runners image is copied recursively from
the locked upstream digest, with no modifications or additional attestations;
every runners tag is checked against that digest. Docker Hub's configured
immutability rule protects build tags. Use a new run with a new UTC-minute build
tag after a partial publish instead of rerunning the same plan.

Only the publishing job receives `DOCKERHUB_TOKEN`, using the repository variable
`DOCKERHUB_USERNAME=aliyusufergin`. Only the final lock-commit job has
`contents: write`. It starts from current `main`, verifies that its build inputs
have not changed since the tested revision, records the verified custom image
index digest and build tag, and pushes a descriptive commit with `GITHUB_TOKEN`.
It never force-pushes. A competing push can reject the commit; start a new run
after resolving the competing change. Workflow-token pushes do not retrigger CI.

Publishing runs are serialized with `cancel-in-progress: false`. A failure stops
the remaining steps and prevents the lock commit. Registry tag updates across
two repositories are not atomic: an interrupted publish may move some tags.
The next successful run republishes all tags to restore pairing. This slice
does not add schedules, push triggers, Sigstore attestations or failure issues.

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
