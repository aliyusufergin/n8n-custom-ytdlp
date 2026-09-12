# n8n-custom-ytdlp

Custom [n8n](https://n8n.io/) image bundled with [yt-dlp](https://github.com/yt-dlp/yt-dlp), so workflows can download and process media directly.

## Status

The custom image can be built and tested locally. Automatic upstream tracking
and publishing are planned separately.

## Build and test locally

Requires Python 3.10+ and Docker with Buildx and a running Linux Docker daemon.
From this checkout, run:

```sh
python3 scripts/build_and_test.py
```

This builds `n8n-ytdlp:local` for the Docker host's architecture (amd64 or arm64)
from [build-inputs.lock.json](build-inputs.lock.json), then runs the Python standard
library image acceptance suite. The build needs network access to Docker Hub and
the pinned GitHub release; the image tests run without external network access.
Readiness is probed over HTTP inside a temporary container, without publishing
a host port. Test containers are removed after use.

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
disabled by default. To enable it while keeping Local File Trigger excluded,
add this deployment setting to your Compose service:

```yaml
environment:
  NODES_EXCLUDE: '["n8n-nodes-base.localFileTrigger"]'
```

Keep the JSON valid: n8n treats invalid JSON in `NODES_EXCLUDE` as an empty list,
which enables every node.

## Locked build inputs

The JSON lock records n8n's version and image index digest, the matching runners
index digest, the yt-dlp nightly tag and both musllinux asset checksums, and
ffmpeg's version and multi-architecture digest. Docker selects the image for the
host architecture; the recipe selects and verifies the corresponding yt-dlp asset.
Build arguments contain only public metadata.

The seed's `published.build_tag` and `published.image_digest` are `null` because
this work has not published an image. A future successful publish will fill
these fields. Local builds generate a UTC build tag for their image labels and
leave the committed lock unchanged.

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
linux/arm64. The local acceptance run for this change uses amd64; native arm64
execution belongs to the later CI work.
