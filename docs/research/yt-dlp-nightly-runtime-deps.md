# yt-dlp nightly distribution and runtime dependencies in a container

Retrieved: 2026-09-10 (all "latest release" facts re-verified 2026-09-11)

Source pins used throughout:

- yt-dlp source at commit [`bbc809a1161d3bfca51fa36f59dda35556ee85a0`](https://github.com/yt-dlp/yt-dlp/tree/bbc809a1161d3bfca51fa36f59dda35556ee85a0), dated 2026-08-30T13:58:45Z. This is `master` HEAD on 2026-09-11 and the source of the latest nightly. Links written as `yt-dlp@bbc809a:<path>` point at this commit.
- yt-dlp wiki at git HEAD `10ac0aaddf237bd71ae79d5c517d59b8a8bcf082` (2026-08-27).
- yt-dlp/FFmpeg-Builds at `0309b22040edfc40b855f3a2d917c39c2d3975af` (2026-09-10).
- denoland/deno_docker at `05f1d8ae2e8f02d8175a12120ccba6045d984791`.

The `n8nio/n8n:latest` image used in the empirical checks was pulled 2026-09-10: n8n `2.38.6` (the `stable` tag was the same image). The n8n base OS itself is researched separately.

## Key findings

**Nightly channel**
- **The latest nightly is `2026.08.30.232658`.** It was published 2026-08-30T23:30:33Z, built from `bbc809a`, and is still latest on 2026-09-11. Nightlies are built only on days that have relevant commits, and master has had none since 2026-08-30. ([release](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/tag/2026.08.30.232658), [release-nightly.yml](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/.github/workflows/release-nightly.yml))
- **Two distribution channels.** Nightly goes out as GitHub releases in `yt-dlp/yt-dlp-nightly-builds` and as PEP 440 dev releases of the `yt-dlp` PyPI package (`2026.8.30.232658.dev0`, wheel uploaded 37 s after the GitHub release). ([README L163-190](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L163-L190), [PyPI](https://pypi.org/project/yt-dlp/2026.8.30.232658.dev0/))
- **Linux assets:**
  - `yt-dlp`: zipimport, 3.07 MB, needs Python ≥ 3.10.
  - `yt-dlp_linux` / `yt-dlp_linux_aarch64`: PyInstaller, glibc 2.17+.
  - `yt-dlp_musllinux` / `yt-dlp_musllinux_aarch64`: PyInstaller, musl 1.2+.
  - Each PyInstaller binary also has a `.zip` onedir variant.

  The PyInstaller builds bundle CPython 3.14.7, curl_cffi 0.16.0 and yt-dlp-ejs 0.8.0, plus the other Python deps. ([README L91-137](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L91-L137), [bundle/requirements/linux.txt](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/bundle/requirements/linux.txt), empirical `-v`)
- **Integrity and authenticity.**
  - Checksums: `SHA2-256SUMS` and `SHA2-512SUMS`, each with a detached GPG `.sig`. The key is `public.key` in the repo, fingerprint `AC0C BBE6 848D 6A87 3464 AF4E 57CF 6593 3B5A 7581`. Both signatures verified "Good".
  - The release has `immutable: true` and a GitHub-issued release attestation covering every asset digest.
  - There are no workflow build-provenance attestations. ([README L126-137](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L126-L137), [public.key](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/public.key))

**YouTube requirements**
- **What YouTube needs.** yt-dlp's README calls `ffmpeg`, `ffprobe`, `yt-dlp-ejs` and a JS runtime "highly recommended", and says yt-dlp-ejs is "Required for full YouTube support". With no JS runtime, yt-dlp falls back to only the `visionos` client and warns "YouTube extraction without a JS runtime has been deprecated, and some formats may be missing". ([README L203-215](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L203-L215), [_video.py L143-147, L2972-2999](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/_video.py#L2972-L2999))
- **Supported JS runtimes, highest priority first:**
  - deno ≥ 2.3.0: the only one enabled by default.
  - node ≥ 22.0.0.
  - quickjs ≥ 2023-12-9, or any QuickJS-NG.
  - bun 1.2.11–1.3.14: deprecated.

  Node must be enabled explicitly with `--js-runtimes node[:PATH]`. ([_jsruntime.py L89-153](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/utils/_jsruntime.py#L89-L153), [options.py L459-479](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/options.py#L459-L479), [wiki EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS))
- **The n8n image's Node qualifies.** It ships Node `26.7.0` at `/usr/local/bin/node`. A system config `/etc/yt-dlp.conf` containing `--js-runtimes node` enabled Node for the non-root `node` user, with no CLI flags (empirical). `node:22-alpine` (22.23.2) and `node:24-alpine` (24.21.0) were also detected as supported.
- **Where the EJS solver scripts come from.** They are bundled in every official binary (PyInstaller and zipimport). A pip install needs `yt-dlp[default]`, which pins `yt-dlp-ejs==0.8.0`. `--remote-components ejs:github|ejs:npm` fetches them at runtime instead: off by default, and not needed with official binaries. ([options.py L481-500](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/options.py#L481-L500), [wiki EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS))
- **yt-dlp's FFmpeg builds are glibc-only.**
  - They currently carry no patches: "currently our builds are equivalent to upstream ffmpeg", and the historical patches are unnecessary "as of 8.0".
  - Only GPL master builds are published for `linux64` and `linuxarm64`.
  - The Linux binaries are static except glibc, which is linked dynamically (needs `GLIBC_2.28`). They fail on Alpine, and on the n8n image (empirical). ([README L207-209](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L207-L209), [FFmpeg-Builds README](https://github.com/yt-dlp/FFmpeg-Builds/blob/0309b22040edfc40b855f3a2d917c39c2d3975af/README.md))
- **Deno has no official musl build.**
  - Deno publishes only `*-unknown-linux-gnu` Linux binaries, and [deno#3711 "Release musl builds"](https://github.com/denoland/deno/issues/3711) is still open.
  - Alpine v3.24 `community` has a native musl `deno` 2.7.4-r2 for x86_64 and aarch64.
  - Deno's official `alpine` image grafts glibc in with patchelf. ([Deno install docs](https://docs.deno.com/runtime/getting_started/installation/), [pkgs.alpinelinux.org](https://pkgs.alpinelinux.org/packages?name=deno&branch=v3.24), [deno_docker alpine.dockerfile](https://github.com/denoland/deno_docker/blob/05f1d8ae2e8f02d8175a12120ccba6045d984791/alpine.dockerfile))
- **Distro packages are not usable as-is.**
  - Alpine `yt-dlp` is the *stable* release (2026.08.19-r0 on v3.24 and edge), not nightly.
  - Debian trixie `yt-dlp` is 2025.04.30.
  - Debian trixie `nodejs` is 20.19.2, below yt-dlp's Node minimum of 22.

  (Checked with `apk`/`apt-cache` in containers; [pkgs.alpinelinux.org](https://pkgs.alpinelinux.org/packages?name=yt-dlp*&branch=v3.24).)
- **PO tokens and cookies are situational.** The PO Token Guide recommends a provider plugin, for example [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider), which is not affiliated with yt-dlp. It needs either a separate HTTP server or a Node/Deno script build. Cookies are "only necessary for content that requires an account", and using them risks an account ban. ([PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide), [Extractors#youtube](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube))

**Container behaviour**
- **Paths that matter for the non-root `node` user (HOME=/home/node):**
  - System config: `/etc/yt-dlp.conf`, `/etc/yt-dlp/config`, `/etc/yt-dlp/config.txt`.
  - System plugins: `/etc/yt-dlp/plugins/<pkg>/yt_dlp_plugins/` or `/etc/yt-dlp-plugins/<pkg>/yt_dlp_plugins/`.
  - Cache: `${XDG_CACHE_HOME:-~/.cache}/yt-dlp`, which is `/home/node/.cache/yt-dlp`.

  ([README L1185-1215](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L1185-L1215), [plugins.py L81-102](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/plugins.py#L81-L102), [cache.py L17-22](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/cache.py#L17-L22))
- **PyInstaller onefile binaries unpack to temp on every run.** They extract into `_MEIxxxxxx` under the temp dir at each start, which is "not compatible" with a `noexec` `/tmp`. The `.zip` onedir variants avoid this. ([PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html))
- **One metadata-only probe succeeded.** Setup: n8n image, `node` user, musllinux nightly, Node enabled via the system config. `--simulate` on `jNQXAC9IVRw` exited 0 with no bot check and picked formats `395+251` via the `visionos` client and HLS. No JS challenge solving happened on this run, so the Node solver path was not exercised end to end (see Empirical checks).

## 1. Nightly channel mechanics

### Where it is published

- **Update channels.** The README defines three: `stable`, `nightly` and `master`. `nightly` "offers releases that publish shortly before midnight UTC on any day that sees changes to the codebase … it is the **recommended channel for regular users**". It is available from [yt-dlp/yt-dlp-nightly-builds](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases) "or as development releases of the `yt-dlp` PyPI package (which can be installed with pip's `--pre` flag)". ([README L163-169](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L163-L169))
- **Scheduling.** The workflow [`release-nightly.yml`](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/.github/workflows/release-nightly.yml) runs on `cron: '23 23 * * *'` (23:23 UTC) or `workflow_dispatch`. It is gated on `vars.BUILD_NIGHTLY`. It releases only if `git log` shows a commit touching `yt_dlp/*.py`, `bundle/*`, `pyproject.toml`, `Makefile` or the build/release workflows since the previously cached nightly commit. The build calls `release.yml` with `prerelease: true`, `target: 'nightly'`, and GPG signing. PyPI publishing goes through trusted publishing (`vars.NIGHTLY_PYPI_PROJECT`).
- **The GitHub `prerelease` flag is `false`** on every release in `yt-dlp-nightly-builds`, so `/releases/latest` works for detection (see below).
- **Self-update.** `yt-dlp --update-to nightly`, or `--update-to nightly@<TAG>`, switches or pins a release binary at runtime. This is not useful for build-time reproducibility. ([README L171-190](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L171-L190))

### Version and tag format

- **GitHub tag.** Format is `YYYY.MM.DD.HHMMSS`: the UTC build timestamp from `strftime('%Y.%m.%d.%H%M%S.%f')`, keeping the first 4 fields ([build.yml L102-109](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/.github/workflows/build.yml#L102-L109)). Example: `2026.08.30.232658`.
- **Source commit.** The release body starts with `Generated from: https://github.com/yt-dlp/yt-dlp/commit/<sha>`, and `yt-dlp -v` prints it for zip and pip builds (`[bbc809a11]`).
- **PyPI version.** This is the same number, PEP 440-normalised (leading zeros dropped), plus `.dev0`. Examples: tag `2026.08.30.232658` → `2026.8.30.232658.dev0`, and tag `2026.08.27.003630` → `2026.8.27.3630.dev0` (both present in the [PyPI JSON](https://pypi.org/pypi/yt-dlp/json)).
- **Version reported by the binary:** `yt-dlp --version` → `2026.08.30.232658`, and `-v` → `nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds (musllinux_exe)`.

### Cadence (observed)

- **Volume.** There were 40 releases between 2026-06-06 and 2026-08-30 (about 3.3/week). There were gaps with no releases, e.g. 2026-07-23→2026-08-04, 2026-08-04→2026-08-16, and none since 2026-08-30 because master is unchanged.
- **Time of day.** Most tags fall between `23:05` and `00:05` UTC, published 3–5 min after the tag timestamp. A few were daytime or off-schedule (probably manual dispatch): `2026.07.04.221833`, `2026.08.16.020253`, `2026.08.17.073947`, `2026.08.18.122307`, `2026.08.27.003630`.
- **Stable.** The latest stable is `2026.08.19` (2026-08-19T23:48:43Z).

### Machine detection (run 2026-09-11)

```
$ gh api repos/yt-dlp/yt-dlp-nightly-builds/releases/latest --jq '{tag_name, published_at, immutable, body: .body[0:90], n_assets: (.assets|length)}'
{"body":"Generated from: https://github.com/yt-dlp/yt-dlp/commit/bbc809a1161d3bfca51fa36f59dda35556","immutable":true,"n_assets":23,"published_at":"2026-08-30T23:30:33Z","tag_name":"2026.08.30.232658"}
```

- **Without `gh`.** The same endpoint works unauthenticated at `https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases/latest` (subject to GitHub's unauthenticated rate limit). Each asset object carries `digest: "sha256:…"`, so checksums can be taken from the API as well as from `SHA2-256SUMS`.
- **PyPI.** `.info.version` returns only the latest *stable* (`2026.8.19`). Nightlies have to be picked out of `.releases`:

```
$ curl -s https://pypi.org/pypi/yt-dlp/json | jq -r '.info.version, ([.releases | keys[] | select(test("dev"))] | sort_by(split(".") | map(tonumber? // 0)) | .[-3:] | join(", "))'
2026.8.19
2026.8.27.231323.dev0, 2026.8.29.232711.dev0, 2026.8.30.232658.dev0
```

### Release assets of `2026.08.30.232658` (23 assets)

| Asset | Size (bytes) | What it is |
|---|---:|---|
| `yt-dlp` | 3,073,725 | zipimport archive with `#!/usr/bin/env python3` shebang. Needs system CPython ≥ 3.10. Bundles `yt_dlp_ejs` but no other deps. |
| `yt-dlp.tar.gz` | 6,024,123 | Source tarball (man pages, completions) |
| `yt-dlp_linux` | 40,454,152 | PyInstaller onefile, x86_64, glibc 2.17+ (ELF interpreter `/lib64/ld-linux-x86-64.so.2`) |
| `yt-dlp_linux.zip` | 40,524,309 | PyInstaller onedir, x86_64, glibc 2.17+ ("no auto-update") |
| `yt-dlp_linux_aarch64` | 40,175,792 | PyInstaller onefile, aarch64, glibc 2.17+ |
| `yt-dlp_linux_aarch64.zip` | 40,222,177 | PyInstaller onedir, aarch64 |
| `yt-dlp_musllinux` | 40,528,968 | PyInstaller onefile, x86_64, musl 1.2+ (interpreter `/lib/ld-musl-x86_64.so.1`) |
| `yt-dlp_musllinux.zip` | 40,673,203 | PyInstaller onedir, x86_64, musl 1.2+ |
| `yt-dlp_musllinux_aarch64` | 39,811,824 | PyInstaller onefile, aarch64, musl 1.2+ |
| `yt-dlp_musllinux_aarch64.zip` | 39,912,917 | PyInstaller onedir, aarch64, musl 1.2+ |
| `yt-dlp_macos`, `yt-dlp_macos.zip` | 37,150,304 / 53,928,073 | macOS 10.15+ universal |
| `yt-dlp.exe`, `yt-dlp_x86.exe`, `yt-dlp_arm64.exe`, `yt-dlp_win.zip`, `yt-dlp_win_x86.zip`, `yt-dlp_win_arm64.zip` | various | Windows |
| `SHA2-256SUMS`, `SHA2-512SUMS` | 1,505 / 2,657 | GNU-style sums for the 18 binaries/archives. The SUMS files, `.sig` files and `_update_spec` are not listed. |
| `SHA2-256SUMS.sig`, `SHA2-512SUMS.sig` | 566 / 566 | Detached GPG signatures |
| `_update_spec` | 2,191 | Self-updater lock rules. Example: `lockV2 yt-dlp/yt-dlp-nightly-builds 2025.10.14.232845 zip Python 3\.9` means zipimport users on Python 3.9 are frozen at that nightly. |

- **No armv7l build in nightly.** Stable `2026.08.19` additionally ships `yt-dlp_linux_armv7l.zip` (glibc 2.31+). Nightly does not, because `release-nightly.yml` does not pass `linux_armv7l`.
- **Asset descriptions** come from [README L91-125](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L91-L125). ELF details come from `file` (empirical).

### What each build bundles

- **Pinned Python deps.** PyInstaller Linux builds (both `linux` and `musllinux`) install [`bundle/requirements/linux.txt`](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/bundle/requirements/linux.txt) with `--require-hashes`: brotli 1.2.0, certifi 2026.7.22, cffi 2.1.1, charset-normalizer 3.5.0, cryptography 50.0.0, curl-cffi 0.16.0, idna 3.18, jeepney 0.9.0, mutagen 1.48.1, pycparser 3.0, pycryptodomex 3.23.0, requests 2.34.2, secretstorage 3.5.0, urllib3 2.7.0, websockets 17.0.1 (Py ≥ 3.11), yt-dlp-ejs 0.8.0. The toolchain is PyInstaller 6.22.0.
- **Python version.** Builds use `PYTHON_VERSION: '3.14'` ([build.yml L127](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/.github/workflows/build.yml#L123-L176), [build.sh](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/bundle/docker/linux/build.sh)).
- **Build and verify images** ([compose.yml](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/bundle/docker/compose.yml)): glibc builds use `ghcr.io/yt-dlp/manylinux2014_{x86_64,aarch64}-shared` (hence glibc 2.17). musl builds use `ghcr.io/yt-dlp/musllinux_1_2_{x86_64,aarch64}-shared` and are verified on `alpine:3.23.2`.
- **Empirical `-v` of `yt-dlp_musllinux`:** `Python 3.14.7 (CPython x86_64 64bit) … (OpenSSL 3.5.8 25 Aug 2026, musl 1)`. `Optional libraries: Cryptodome-3.23.0, brotli-1.2.0, certifi-2026.07.22, curl_cffi-0.16.0, mutagen-1.48.1, requests-2.34.2, secretstorage-3.5.0, sqlite3-3.53.4, urllib3-2.7.0, websockets-17.0.1, yt_dlp_ejs-0.8.0`. `Request Handlers: urllib, requests, websockets, curl_cffi`. `yt-dlp_linux` shows the same set.
- **zipimport `yt-dlp`.** The Makefile's `yt-dlp-extra` target downloads the `yt_dlp_ejs-0.8.0` wheel (hash-pinned) and zips `yt_dlp_ejs/**` into the executable ([Makefile L200-240](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/Makefile#L200-L240)). With Debian's python3 3.13.5 its header showed only `Optional libraries: sqlite3-3.46.1, yt_dlp_ejs-0.8.0`: no certifi, brotli, websockets, requests, mutagen, pycryptodomex or curl_cffi unless the system provides them. The README confirms curl_cffi is "included in most builds *except* `yt-dlp` (Unix zipimport binary)" ([README L229](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L223-L229)).
- **PyPI wheel.** It contains only Unlicense code ([README L149](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L139-L149)) and has no required deps (`dependencies = []`). The extras in [pyproject.toml](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/pyproject.toml) are:

  | Extra | Contents |
  |---|---|
  | `default` | ranges for brotli, certifi, mutagen, pycryptodomex, requests, urllib3, websockets; exact `yt-dlp-ejs==0.8.0` |
  | `curl-cffi` | `curl-cffi>=0.5.10,!=0.6.*..!=0.9.*,<0.17` |
  | `secretstorage` | secretstorage |
  | `deno` | `deno>=2.6.6` (the PyPI deno package) |
  | `pin` | exact versions of the `default` set |
  | `pin-curl-cffi` | exact versions of the curl-cffi set |
  | `pin-secretstorage` | exact versions of the secretstorage set |
  | `pin-deno` | `deno==2.9.5` |

### Integrity and authenticity verification

1. **Checksums.** `sha256sum --ignore-missing -c SHA2-256SUMS` (GNU coreutils). BusyBox `sha256sum` (the n8n image) has no `--ignore-missing`, so use `grep ' yt-dlp_musllinux$' SHA2-256SUMS | sha256sum -c -` (worked empirically). Better for reproducibility: hard-code the sha256 in the Dockerfile.
2. **GPG.** The README gives `curl -L https://github.com/yt-dlp/yt-dlp/raw/master/public.key | gpg --import` then `gpg --verify SHA2-256SUMS.sig SHA2-256SUMS` ([README L131-137](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L131-L137)). Key: `rsa4096 2023-02-26 [SC] AC0CBBE6848D6A873464AF4E57CF65933B5A7581`, uid `Simon Sawicki (yt-dlp signing key) <contact@grub4k.xyz>`. Empirically both `.sig` files were "Good signature", made 2026-08-30 23:30:01 UTC. Pin the fingerprint instead of trusting a freshly downloaded key.
3. **GitHub immutable release and release attestation.**
   - The latest nightly and the latest stable report `"immutable": true`. yt-dlp/FFmpeg-Builds `latest` is `false`.
   - `GET /repos/yt-dlp/yt-dlp-nightly-builds/attestations/sha256:<asset digest>` returns a Sigstore bundle. Its in-toto predicate is `https://in-toto.io/attestation/release/v0.2`, with subject `pkg:github/yt-dlp/yt-dlp-nightly-builds@2026.08.30.232658` plus the sha256 of all 23 assets. It is signed with a GitHub certificate (SAN `https://dotcom.releases.github.com`, initiator `github`).
   - GitHub documents verification with `gh release verify RELEASE-TAG` and `gh release verify-asset RELEASE-TAG ARTIFACT-PATH` ([GitHub docs](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/verifying-the-integrity-of-a-release)). These were **not executed** here: local `gh` 2.46.0 lacks the subcommands.
   - The same digest queried on `yt-dlp/yt-dlp` returns 404. yt-dlp's workflows at `bbc809a` contain no `attest-build-provenance` step; the only `gh attestation verify` checks actionlint in [`test-workflows.yml`](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/.github/workflows/test-workflows.yml).
4. **The built-in updater** checks only the SHA-256 from `SHA2-256SUMS`, not GPG ([update.py L475, L547](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/update.py#L475)).

### Reproducible pinning per install method

- **Standalone binary.** `https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/<TAG>/<asset>` plus a hard-coded sha256 (e.g. `yt-dlp_musllinux` = `a70990ba6858c4215aeab7f629290079b9575713079bcb7da4368ff1d55c5021`, `yt-dlp_musllinux_aarch64` = `6b1e6b9ad1b6a4dfd9a45c916ddbc2ccebb6936d480a75fceb3d78bd3b46f757`). Because the release is immutable, the asset cannot be swapped under the tag. Avoid `releases/latest/download/…` in builds.
- **zipimport.** Same URL scheme (`yt-dlp` = `3f1b267b4488f3aed3731a9e84a44011ca5569901868532e10ee11fd07d69707`). The system Python and its packages must be pinned separately.
- **pip.** `pip install "yt-dlp[default]==2026.8.30.232658.dev0"`; an exact `==` pin on a dev version does not need `--pre`. Wheel sha256: `a2554b665e11ad857ac6a56941644d8459cb94ebd97291c88ba5af9bfc30e637`.
  - Empirically `[default,curl-cffi]` resolved *newer* transitive versions than yt-dlp's own pins: curl_cffi 0.16.3, websockets 17.1, idna 3.19, charset-normalizer 3.5.1, versus the pinned 0.16.0 / 17.0.1 / 3.18 / 3.5.0.
  - For determinism use `yt-dlp[pin,pin-curl-cffi]==<ver>`, or a hashed lock file with `--require-hashes`.

## 2. Official dependency list (README at `bbc809a`)

Source: [README L195-253](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L195-L253). The README marks with `*` the packages included in standalone binaries.

**Python.** "Python versions 3.10+ (CPython) and 3.11+ (PyPy) are supported." `pyproject.toml` has `requires-python = ">=3.10"`, and classifiers list 3.10–3.14. The README adds: "While all the other dependencies are optional, `ffmpeg`, `ffprobe`, `yt-dlp-ejs` and a supported JavaScript runtime/engine are highly recommended".

| Group | Dependency | Purpose (README) | What breaks without it |
|---|---|---|---|
| Strongly recommended | **ffmpeg + ffprobe** | "Required for merging separate video and audio files, as well as for various post-processing tasks" | No merging, so the default format spec falls back to `best/bestvideo+bestaudio` (seen in the probe with no ffmpeg). No `-x`, embedding, remuxing or conversion. |
| Strongly recommended | **yt-dlp-ejs** | "Required for full YouTube support" | YouTube signature/n challenges can't be solved: "Signature solving failed / n challenge solving failed: Some formats may be missing" ([_video.py L3345-3356](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/_video.py#L3345-L3356)) |
| Strongly recommended | **JS runtime** (deno recommended; node, bun, QuickJS) | "also required to run yt-dlp-ejs" | Only the JS-less `visionos` client is used, with a deprecation warning (section 3) |
| Networking | certifi* | Mozilla CA bundle | Relies on the system CA store |
| Networking | brotli* / brotlicffi | Brotli content-encoding | Brotli responses unsupported |
| Networking | websockets* | "For downloading over websocket" | Websocket-based downloads unavailable |
| Networking | requests* | "For HTTPS proxy and persistent connections support" | No HTTPS proxies; urllib handler only |
| Impersonation | curl_cffi (recommended) | Browser TLS impersonation, "may be required for some sites that employ TLS fingerprinting" | `--impersonate` unavailable (situational; not YouTube-specific) |
| Metadata | mutagen* | `--embed-thumbnail` in certain formats | Thumbnail embedding limited |
| Metadata | AtomicParsley | mp4/m4a thumbnail embedding fallback | Situational |
| Metadata | xattr / pyxattr / setfattr | `--xattrs` on Mac/BSD | Not relevant on Linux containers |
| Misc | pycryptodomex* | "decrypting AES-128 HLS streams and various other data" | Encrypted HLS handling degraded |
| Misc | phantomjs | Some non-YouTube extractors; "No longer used for YouTube. To be deprecated" | Irrelevant for YouTube |
| Misc | secretstorage* | `--cookies-from-browser` GNOME keyring (Chromium) on Linux | Irrelevant in a headless container |
| Misc | external downloaders | `--downloader` | Situational |
| Deprecated | rtmpdump | rtmp; use `--downloader ffmpeg` | — |

"If you do not have the necessary dependencies for a task you are attempting, yt-dlp will warn you. All the currently available dependencies are visible at the top of the `--verbose` output."

### ffmpeg / ffprobe: yt-dlp builds vs distro builds

- **yt-dlp's stance.** "Since ffmpeg is such an important dependency, we provide our own builds at yt-dlp/FFmpeg-Builds. In the past, patches were applied to these builds in order to fix common issues for yt-dlp users, but currently our builds are equivalent to upstream ffmpeg." ([README L209](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L207-L211)). It also warns against the PyPI `ffmpeg` Python package.
- **FFmpeg-Builds README** ([@0309b22](https://github.com/yt-dlp/FFmpeg-Builds/blob/0309b22040edfc40b855f3a2d917c39c2d3975af/README.md)):
  - "Patches Applied: Currently, no patches are being applied to the builds."
  - "Historical Patches … no longer needed as of **8.0**": AAC HLS truncation, YouTube VP9 non-monotonous DTS, Windows long paths, chapter embedding regression, WebVTT decoding, Vulkan NULL type, non-standard HEVC in FLV, …
  - Known unfixed issues: removing a segment before the first subtitle, long HLS playlists.
  - "The builds provided are only meant to be used with yt-dlp".
- **Practical takeaway.** Upstream or distro ffmpeg ≥ 8.0 is functionally equivalent. Alpine v3.24 ships `ffmpeg-8.1.2-r0`. Debian trixie ships `7.1.5`, which predates 8.0, so some historical fixes may be missing (not verified).
- **Published assets.** Release `latest` ("Latest Auto-Build (2026-09-10 22:10)" on 2026-09-11) has `checksums.sha256`, `ffmpeg-master-latest-linux64-gpl.tar.xz` (~128.5 MB) and `ffmpeg-master-latest-linuxarm64-gpl.tar.xz` (~109.9 MB), plus Windows `win32`/`win64`/`winarm64` in `gpl` and `gpl-shared`.
  - **No LGPL, no shared Linux builds, no release-branch builds.** The build matrix builds Linux only as `linux64`/`linuxarm64` × `gpl` ([build.yml](https://github.com/yt-dlp/FFmpeg-Builds/blob/0309b22040edfc40b855f3a2d917c39c2d3975af/.github/workflows/build.yml)). The `variants/` dir still contains lgpl/nonfree scripts, but they are unused. The README intro mentions "latest release branch (release/7.1)", which is stale relative to the published assets.
  - **Tags.** `latest` is a rolling release with stable file names and `immutable: false`. Dated `autobuild-YYYY-MM-DD-HH-MM` releases use versioned names, e.g. `autobuild-2026-09-10-22-10` → `ffmpeg-N-126495-g3a165c77dc-linux64-gpl.tar.xz`, and `autobuild-2026-09-06-16-53` → `ffmpeg-N-126435-gf93cd72dde-linux64-gpl.tar.xz`. Builds run daily, and older dated releases are pruned (37 releases on 2026-09-11, oldest `autobuild-2024-10-31-14-17`).
  - **Checksums.** `checksums.sha256` is sha256-only, with no signatures. To pin, use the `autobuild-*` tag, the versioned filename and the sha256.
- **"Static" means static except glibc** (empirical, 2026-09-06 x86_64 build):
  - `file` reports `ELF 64-bit LSB pie executable … dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 4.18.20`. The highest symbol version is `GLIBC_2.28`. Sizes: ffmpeg 141 M, ffprobe 140 M, ffplay 142 M.
  - The toolchain is `x86_64-ffbuild-linux-gnu` (crosstool-NG, gcc 15.2.0). Its base image deletes `libc.a`, `libm.a`, `libpthread.a` etc. to force a dynamic libc ([images/base-linux64/Dockerfile](https://github.com/yt-dlp/FFmpeg-Builds/blob/0309b22040edfc40b855f3a2d917c39c2d3975af/images/base-linux64/Dockerfile)).
  - Result: the build runs on Debian trixie (glibc 2.41) but **not on musl**. On `alpine:3`: `not found`. With `gcompat`: `Error loading shared library libmvec.so.1` and `libgcc_s.so.1`. On the n8n image: `libmvec.so.1 … fcntl64: symbol not found`.
  - arm64 was not checked but uses the same toolchain approach.
- **musl alternatives.**
  - Alpine `ffmpeg` apk, a shared build with a large dependency closure.
  - Third-party fully static builds, e.g. [wader/static-ffmpeg](https://github.com/wader/static-ffmpeg): "hardened static PIE binaries with no external dependencies that can be used with any base image", `COPY --from=mwader/static-ffmpeg:9.0.1 /ffmpeg /usr/local/bin/`. Not affiliated with yt-dlp.

## 3. YouTube today: external JavaScript runtime (EJS)

**What EJS is.** The wiki ([EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS)) says: "To download from YouTube, yt-dlp needs to solve JavaScript challenges presented by YouTube using an external JavaScript runtime. This involves running challenge solver scripts maintained at yt-dlp-ejs." EJS "replaces the prior JSInterp and PhantomJS based approach. For YouTube both are no longer used."

### Supported runtimes

| Runtime | Min version (code) | Default | Enable | Notes (wiki / code) |
|---|---|---|---|---|
| deno | `(2, 3, 0)` | **enabled** | `--js-runtimes deno:/path` for a custom path | Recommended. Run with `--ext=js --no-code-cache --no-prompt --no-remote --no-lock --node-modules-dir=none --no-config`, plus `--no-npm` unless the npm variant is used ([deno.py](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/jsc/_builtin/deno.py)). "restricted permissions (e.g, no file system or network access)". Download `deno`, not `denort`. |
| node | `(22, 0, 0)` | off | `--js-runtimes node` or `node:/path/to/node` | "Runs code with *some* permissions restricted". yt-dlp runs `node --permission -` (≥ 23.5.0) or `--experimental-permission --no-warnings=ExperimentalWarning -` (< 23.5.0), with the script on stdin ([node.py](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/jsc/_builtin/node.py)). |
| quickjs / quickjs-ng | QuickJS `(2023, 12, 9)`; any QuickJS-NG | off | `--js-runtimes quickjs[:path]`; the executable must be named `qjs` | QuickJS < 2025-4-26 or QuickJS-NG < 0.12.0 "can lead to execution times of several minutes". Uses temp files (the wiki notes TOCTOU risk). |
| bun | `(1, 2, 11)`, max `(1, 3, 14)` | off | `--js-runtimes bun[:path]` | **Deprecated** ([issue #16766](https://github.com/yt-dlp/yt-dlp/issues/16766)). "No permission restrictions available". |

Minimum versions are from [`_jsruntime.py` L89-153](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/utils/_jsruntime.py#L89-L153).

**Priority and defaults** ([options.py L459-479](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/options.py#L459-L479)):
- "Supported runtimes are (in order of priority, from highest to lowest): deno, node, quickjs, bun. Only "deno" is enabled by default. The highest priority runtime that is both enabled and available will be used."
- `--js-runtimes` *adds* to the default list. To prefer node while deno is installed, pass `--no-js-runtimes --js-runtimes node`.
- Python API: `js_runtimes={'node': {'path': '/usr/local/bin/node'}}`, where `None` means `{'deno': {}}` ([YoutubeDL.py L543-554, L739](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/YoutubeDL.py#L543-L554)).

**Runtime lookup.** Without a path, yt-dlp checks the Python scripts dir. On non-Windows it otherwise passes the bare name to `Popen`, i.e. a `PATH` lookup ([`_find_exe`](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/utils/_jsruntime.py#L16-L56)). In n8n, `PATH` includes `/usr/local/bin`.

**Config-file equivalent.** Config files take the same options as the CLI. `/etc/yt-dlp.conf` containing `--js-runtimes node` produced `[debug] System config "/etc/yt-dlp.conf": ['--js-runtimes', 'node']` and `[debug] JS runtimes: node-26.7.0` for the `node` user (empirical). The wiki recommends adding the flag to the config file for node, bun and quickjs.

**Debug header output** ([YoutubeDL.py L4168-4178](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/YoutubeDL.py#L4168-L4178)):
- `JS runtimes: none (disabled)` when `--no-js-runtimes` is given.
- Otherwise it lists the enabled runtimes that were detected, e.g. `node-26.7.0`, appending ` (unsupported)` when below the minimum.
- `none` means an enabled runtime was not found.

**The n8n 2.x Node qualifies.** The minimum is 22.0.0. Measured: n8n 2.38.6 image `v26.7.0`; `node:24-alpine` `v24.21.0`; `node:22-alpine` `v22.23.2`. All were printed as supported, with no ` (unsupported)` suffix.

### yt-dlp-ejs and challenge-solver scripts

- **Package.** [yt-dlp/ejs](https://github.com/yt-dlp/ejs) latest release is `0.8.0` (2026-03-17). Assets: `yt.solver.core.js`/`.min.js`, `yt.solver.lib.js`/`.min.js` (bundles meriyah ISC + astring MIT), `yt.solver.deno.lib.js`, `yt.solver.bun.lib.js`, and the wheel/sdist. PyPI `yt-dlp-ejs` 0.8.0 requires Python ≥ 3.10.
- **Script sources, in order** ([ejs.py L259-299](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/jsc/_builtin/ejs.py#L259-L299)):
  1. `PYPACKAGE`: the installed `yt_dlp_ejs`.
  2. `CACHE`: previously downloaded scripts, in cache section `challenge-solver`.
  3. `BUILTIN`: vendored in `yt_dlp/extractor/youtube/jsc/_builtin/vendor/`. The git tree has only `yt.solver.core.js`, `yt.solver.deno.lib.js` and `yt.solver.bun.lib.js`, not the full `lib`, because of licensing.
  4. `WEB`: `https://github.com/yt-dlp/ejs/releases/download/<VERSION>/yt.solver.{lib,core}.min.js`, only if `ejs:github` is allowed.
- **Integrity of loaded scripts.** Every script's major.minor version must match `VERSION = '0.8.0'`, and its SHA3-512 must match `HASHES` in [`vendor/_info.py`](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/jsc/_builtin/vendor/_info.py), unless the dev extractor-arg `youtube-ejs:dev=true` is set. A mismatch rejects the script.
- **Which distributions include the scripts** (wiki table, confirmed empirically via `yt_dlp_ejs-0.8.0` in `-v`):
  - Official PyInstaller executables and the zipimport binary: bundled, "No additional action required".
  - PyPI installs: `pip install -U "yt-dlp[default]"`. Installing `yt-dlp-ejs` separately is allowed, but "The version MUST match the version specified in yt-dlp's pyproject.toml".
  - Third-party packages: depends on the packager. Alpine ships `yt-dlp-ejs-0.8.0-r1` as a dependency of `yt-dlp`, installed to `/usr/lib/python3.14/site-packages/yt_dlp_ejs/`. No Debian trixie package was found.

### `--remote-components`

([options.py L481-500](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/options.py#L481-L500), [wiki EJS options 2-3](https://github.com/yt-dlp/yt-dlp/wiki/EJS#option-2-enable-ejs-script-downloads-from-npm))

- **Values.** Default `[]`. Supported: `ejs:npm` ("external JavaScript components from npm") and `ejs:github`. The help text says: "This option is currently not needed if you are using an official executable or have the requisite version of the yt-dlp-ejs package installed."
- **`ejs:npm`** works with deno and bun only. The deno lib script imports `npm:meriyah@6.1.4` and `npm:astring@1.9.0` (exact versions). yt-dlp hashes the lib script, but deno fetches the npm packages with `--no-lock` (inference from code: npm package contents are not hash-checked by yt-dlp). Deno can reuse already-cached npm packages without the flag (`--cached-only` probe).
- **`ejs:github`** downloads the exact `0.8.0` release files and stores them in the yt-dlp cache (`~/.cache/yt-dlp/challenge-solver/`). They are hash-verified against the pinned SHA3-512. It needs GitHub reachability; the wiki notes it "may not work … with an IPv6 IP-only".
- **Implications.** Both values add runtime network fetches and writes to HOME/cache, making behaviour depend on external availability. The npm path adds unpinned-content trust. For an image that uses the official binary, neither is needed; leave the default (none).

### Consequence of no JS runtime

- **Client selection** ([_video.py L143-147](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/_video.py#L143-L147)): `_DEFAULT_CLIENTS = ('visionos', 'web')`, `_DEFAULT_JSLESS_CLIENTS = ('visionos',)`, `_DEFAULT_AUTHED_CLIENTS = ('web_embedded', 'tv_downgraded', 'web')`, `_DEFAULT_PREMIUM_CLIENTS = ('web_creator', 'tv_downgraded', 'web')`.
- **Warning.** If no JSC provider is available and no `player_client` is requested, yt-dlp uses the JS-less set and warns: "No supported JavaScript runtime could be found. Only deno is enabled by default; to use another runtime add --js-runtimes RUNTIME[:PATH] to your command/config. YouTube extraction without a JS runtime has been deprecated, and some formats may be missing." ([L2972-2999](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/_video.py#L2972-L2999))
- **Failure.** If challenges remain unsolved: "Signature solving failed: Some formats may be missing" and "n challenge solving failed: Some formats may be missing".
- **Age-restricted** handling also checks runtime availability ([L3150-3171](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/extractor/youtube/_video.py#L3150-L3171)).

## 4. YouTube reliability extras

### PO tokens

Sources: [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide), [Extractors#youtube](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube).

- **What they are.** "Proof of Origin (PO) Token is a parameter that YouTube requires to be sent with requests from some clients. Without it, requests for the affected clients' format URLs may return HTTP Error 403, or result in your account or IP address being blocked."
- **yt-dlp's default approach.** "By default, yt-dlp will attempt to download videos using clients that do not currently require a PO Token. However, some formats and features may not be available without the token(s)." TL;DR: "Use a PO Token Provider plugin to provide the `mweb` client with a PO Token for GVS requests."
- **Enforcement table:**
  - `web`: Subs, GVS (SABR only).
  - `web_safari`: GVS\* (HLS doesn't need it).
  - `mweb`, `web_music`, `tv_simply`: GVS.
  - `web_creator`: GVS (account cookies needed).
  - `android`, `ios`: GVS or Player.
  - `tv`: not required (all formats DRM'd without cookies).
  - `web_embedded`: not required (embeddable videos only).
  - `android_vr`: not required (no "made for kids").

  PO tokens are not required for Premium GVS, or for HLS live (except `ios`). Tokens are bound to the video ID, so manual extraction is "no longer recommended".
- **Featured providers.** Both are "not affiliated with yt-dlp".
  - [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider): "Maintained by a yt-dlp maintainer". Latest `2.0.0` (2026-09-08).
    - Requirements: yt-dlp ≥ 2025.05.22.
    - Provider option (a) is an HTTP server on `127.0.0.1:4416`, available as a Docker image `brainicism/bgutil-ytdlp-pot-provider` (node or deno flavors). It is unauthenticated, so bind it to loopback only.
    - Provider option (b) is a script: Node ≥ 20 or Deno ≥ 2.0.0, plus `git clone`, `npm ci`, `npx tsc` (native `canvas` dep). "NOT recommended for high concurrency".
    - Plugin install: `pip install bgutil-ytdlp-pot-provider`, or drop `bgutil-ytdlp-pot-provider.zip` into a yt-dlp plugin folder. The zip is the only route for the PyInstaller binary, since "Any path in `PYTHONPATH`… does not apply for Pyinstaller builds" ([README Plugins](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L1992-L2045)).
    - Non-default server URL: `--extractor-args "youtubepot-bgutilhttp:base_url=…"`.
    - Its own caveat: "Providing a PO token does not guarantee bypassing 403 errors or bot checks". It states it "was used to bypass the 'Sign in to confirm you're not a bot' message when invoking yt-dlp from an IP address flagged by YouTube".
  - [yt-dlp-getpot-wpc](https://github.com/coletdjnz/yt-dlp-getpot-wpc): "Maintained by a yt-dlp core maintainer". Needs Chrome/Chromium (nodriver), pip only, yt-dlp ≥ 2025.09.26. Not practical inside the n8n image.
- **Verbose output** in the probe: `[youtube] [pot] PO Token Providers: none`.

### Cookies, rate limits, bot checks

- **Cookies** ([Extractors#exporting-youtube-cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)):
  - "This is only necessary for content that requires an account to access, such as private playlists, age-restricted videos and members-only content."
  - Caution: "By using your account with yt-dlp, you run the risk of it being banned".
  - Export from a private window after navigating to `https://www.youtube.com/robots.txt`, then close the window, so cookies are never rotated.
  - Pass as `--cookies FILE` in Netscape format ([FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)). OAuth login no longer works.
- **Rate limits.** "This content isn't available, try again later" means the rate limit was hit. Guest ≈ 300 videos/h (≈ 1000 webpage/player requests/h); account ≈ 2000 videos/h. The wiki recommends a 5–10 s sleep (`-t sleep`).
- **Blocked IPs.** For HTTP 429/402 the FAQ suggests solving a CAPTCHA and passing cookies, or using `--proxy` / `--source-address` ([FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#http-error-429-too-many-requests-or-402-payment-required)).
- **"Sign in to confirm you're not a bot"** has no dedicated section in the EJS, FAQ, PO Token Guide or Extractors (YouTube) wiki pages at wiki HEAD `10ac0aa`. The only first-party-adjacent mention found is the bgutil README quoted above. Datacenter-IP behaviour was not tested here.

### Classification

| Item | Class |
|---|---|
| yt-dlp nightly (recent) | Required |
| JS runtime (node ≥ 22 / deno ≥ 2.3) + yt-dlp-ejs 0.8.0 | Required for full YouTube support (README); without it the path is deprecated and formats are missing |
| ffmpeg + ffprobe | Required in practice (best quality is usually separate video+audio) |
| certifi, brotli, websockets, requests, mutagen, pycryptodomex | Recommended (bundled in PyInstaller binaries) |
| Writable cache dir (`~/.cache/yt-dlp`) | Recommended |
| curl_cffi | Situational (TLS-fingerprinting sites; bundled anyway) |
| PO token provider plugin + provider service | Situational (403s, flagged or datacenter IPs, `mweb`/`web` clients) |
| Cookies file | Situational (age-restricted, private or members content; bot checks), with ban risk |
| Proxy / sleep options | Situational (rate limits, IP blocks) |
| secretstorage, AtomicParsley, xattr, phantomjs, rtmpdump | Not needed for YouTube in a headless container |

## 5. Installing into a container image

### (a) Alpine / musl with `apk`

Package versions below were checked with `apk search -e -x` inside `alpine:3` (= `3.24.1`) and `alpine:edge` (= `3.25.0_alpha20260805`) on 2026-09-10; arches from [pkgs.alpinelinux.org](https://pkgs.alpinelinux.org/packages?name=yt-dlp*&branch=v3.24).

| Package | v3.24 | edge |
|---|---|---|
| `yt-dlp` / `yt-dlp-core` | 2026.08.19-r0 (stable; community; all 9 arches) | 2026.08.19-r0 |
| `yt-dlp-ejs` | 0.8.0-r1 | 0.8.0-r1 |
| `ffmpeg` | 8.1.2-r0 | 8.1.2-r1 |
| `deno` | 2.7.4-r2 (community; x86_64, aarch64; native musl) | 2.7.4-r3 |
| `nodejs` / `nodejs-current` | 24.18.1-r0 / 26.5.1-r0 | 24.18.1-r2 / 26.8.1-r0 |
| `quickjs` / `quickjs-ng` | 0.20250913-r0 / 0.11.0-r2 (< 0.12.0: slow) | 0.20260604-r0 / 0.16.2-r0 |
| `python3` | 3.14.7-r1 | 3.14.7-r0 |
| `py3-brotli`, `py3-certifi`, `py3-mutagen` | 1.2.0-r1, 2026.2.25-r1, 1.47.0-r2 | 1.2.0-r1, 2026.7.22-r0, 1.48.0-r0 |
| `py3-pycryptodomex`, `py3-requests`, `py3-urllib3` | 3.23.0-r1, 2.33.1-r0, 2.7.0-r0 | 3.23.0-r1, 2.34.2-r0, 2.7.0-r0 |
| `py3-websockets`, `py3-secretstorage` | 16.0-r1, 3.5.0-r1 | 17.1-r0, 3.5.0-r1 |
| `py3-curl-cffi` | not packaged | not packaged |

**Alpine's own yt-dlp package.** `apk info -R yt-dlp` lists `attr ca-certificates ffmpeg py3-brotli py3-mutagen py3-pycryptodomex py3-secretstorage py3-websockets yt-dlp-ejs yt-dlp-core=2026.08.19-r0`, and `yt-dlp-core` needs `python3~3.14`. There is no JS runtime dependency, and no requests, certifi or curl_cffi. The wiki's Alpine notes: `apk -U add yt-dlp` / `yt-dlp-core`, "Make sure you're on the latest version (or edge)" ([Installation](https://github.com/yt-dlp/yt-dlp/wiki/Installation#alpine-linux)).

**Install methods on musl:**

1. **`yt-dlp_musllinux[_aarch64]` onefile.** One 38.7 MiB file that bundles Python 3.14.7 and all deps (incl. curl_cffi and ejs). No system Python needed.
   - Gotchas: extraction into `$TMPDIR/_MEI*` on every run (startup cost; `/tmp` must be writable and exec). The `.zip` onedir avoids extraction but needs `unzip`.
   - Add ffmpeg (`apk add ffmpeg`, or a static copy) and a JS runtime (`nodejs`/`deno` apk, or the base image's node). **Lowest complexity.**
2. **zipimport `yt-dlp` + `apk add python3 py3-…`.** 3 MB plus about 73 MB of Python stdlib (`/usr/lib/python3.14` measured). Deps come as distro py3 packages (no curl_cffi); ejs is bundled.
3. **venv + pip `yt-dlp[default,curl-cffi]==2026.8.30.232658.dev0`** on apk `python3`. The venv measured 98.8 MB (musllinux wheels installed without compilers). Pinned via `[pin,pin-curl-cffi]` or a hashed lock. Allows pip-installed plugins such as `bgutil-ytdlp-pot-provider`.
4. **`apk add yt-dlp`.** Stable only, lagging nightly; empirical `-v`: `stable@2026.08.19`, no requests/curl_cffi. **Does not meet the nightly requirement.**

**n8n image caveat (observation).** `n8nio/n8n:2.38.6` is a Docker Hardened Image (`com.docker.dhi.version=26.7.0-alpine3.24-dev`, `/etc/os-release` "Docker Hardened Images (Alpine)" `VERSION_ID=3.24`). Its apk binary is absent (`sh: apk: not found`), although `/etc/apk/repositories` exists. There is no python3, ffmpeg, curl, gpg or xz. Present: `wget`, `sha256sum`, `tar`, `unzip`, and musl `1.2.6`. So at runtime it behaves like scenario (c); packages must come from a multi-stage build or be copied in.

### (b) Debian / glibc with `apt`

Checked with `apt-cache policy` in `debian:stable-slim` = Debian 13.6 "trixie" (glibc 2.41), 2026-09-10:
- `yt-dlp` 2025.04.30-1
- `ffmpeg` 7:7.1.5-0+deb13u1
- `nodejs` 20.19.2+dfsg-1+deb13u2 (**below yt-dlp's 22.0.0 minimum**)
- `python3` 3.13.5-1
- `quickjs` 2025.04.26-1
- `python3-brotli` 1.1.0-2+b7, `python3-mutagen` 1.47.0-1, `python3-pycryptodome` 3.20.0+dfsg-3, `python3-websockets` 15.0.1-1
- No candidates for `deno`, `yt-dlp-ejs` / `python3-yt-dlp-ejs` or `python3-curl-cffi`.
- The apt `yt-dlp` Depends on python3-certifi, -mutagen, -pycryptodome, -requests, -urllib3, -websockets, and Recommends ffmpeg, aria2|wget|curl, ca-certificates.

**Install methods on glibc:**

1. **`yt-dlp_linux[_aarch64]`** (glibc ≥ 2.17) plus **yt-dlp FFmpeg-Builds `linux64-gpl`/`linuxarm64-gpl`** (glibc ≥ 2.28). Both copy in with no apt deps. Empirically `-v` showed `exe versions: ffmpeg N-126435-gf93cd72dde-20260906 (setts), ffprobe …`. The FFmpeg-Builds tarball ships `ffplay` too (≈ 140 MB each uncompressed; drop ffplay).
2. **zipimport + `apt install python3`** (3.13.5 qualifies). Other deps must come from `python3-*` apt packages (older) or pip.
3. **venv + pip pinned** (as in (a)).
4. **JS runtime.** apt `nodejs` 20 is too old. Options: `quickjs` 2025.04.26 from apt (meets the "optimized" threshold), the official Deno `deno-{x86_64,aarch64}-unknown-linux-gnu.zip` (latest `v2.9.6`, 2026-08-27, with `.sha256sum` files), or a Node ≥ 22 from outside Debian.
5. **`apt install yt-dlp`** is 2025.04.30 and not viable.

### (c) Minimal image without a package manager (copy-in only)

- **yt-dlp.** Copy the PyInstaller binary that matches the libc. `yt-dlp_musllinux` on glibc fails with `sh: 3: /dl/yt-dlp_musllinux: not found` (missing musl loader, empirical). The glibc build needs `/lib64/ld-linux-*` (per the README; not tested on musl). The zipimport build is impossible without Python.
- **Checksums.** Verify at build time. BusyBox `sha256sum -c -` with a grep'd line works; GNU `--ignore-missing` is not available in BusyBox.
- **ffmpeg.** glibc base: yt-dlp FFmpeg-Builds tarball (needs `xz`, so extract in a builder stage). musl base: a fully static third-party build (e.g. `COPY --from=mwader/static-ffmpeg:<ver> /ffmpeg /ffprobe`), or Alpine `ffmpeg` together with its full shared-library closure, which must match the base's Alpine release.
- **JS runtime.** Use the node already in the image with `--js-runtimes node` in `/etc/yt-dlp.conf`. The alternative is Deno: official binaries are glibc-only ([deno#3711](https://github.com/denoland/deno/issues/3711) open; musl build PRs [#36129](https://github.com/denoland/deno/pull/36129) and [#36203](https://github.com/denoland/deno/pull/36203) open). Deno's official alpine image copies glibc from `gcr.io/distroless/cc` into `/usr/local/lib/glibc` and patchelfs the rpath. Alpine's native `deno` (`deno 2.7.4 (stable, release, x86_64-alpine-linux-musl)`) is 105.3 MB. `ldd` shows it dynamically linked against musl, libzstd, libz, liblcms2, libffi, libsqlite3, libstdc++, libatomic, ICU 78 (`libicui18n`/`libicuuc`/`libicudata`), libsimdutf and libgcc_s. Copying it into another image means copying that whole closure from the same Alpine release.
- **Size comparison.** musllinux yt-dlp is ≈ 39 MiB. Deno adds ≈ 100 MB. Node is ≈ 0 extra if the base already has it.

### Config, plugin and cache paths

**Config files** ([README L1185-1215](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L1185-L1215); dirs from [utils/_utils.py L4742-4758](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/utils/_utils.py#L4742-L4758)), loaded in this order:
1. `--config-locations`.
2. Portable: `yt-dlp.conf` next to the binary.
3. Home: `yt-dlp.conf` in the `-P` path, **or the current directory** if `-P` is not given.
4. User: `${XDG_CONFIG_HOME}/yt-dlp.conf`, `${XDG_CONFIG_HOME}/yt-dlp/config` (recommended), `${XDG_CONFIG_HOME}/yt-dlp/config.txt`, `~/yt-dlp.conf`, `~/yt-dlp.conf.txt`, `~/.yt-dlp/config`, `~/.yt-dlp/config.txt`. `XDG_CONFIG_HOME` defaults to `~/.config`.
5. System: `/etc/yt-dlp.conf`, `/etc/yt-dlp/config`, `/etc/yt-dlp/config.txt`.

`--ignore-config` on the CLI disables all config files, including a system `--js-runtimes node`. `--ignore-config` inside the system config prevents the user config from loading.

**Plugins** ([README Plugins](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/README.md?plain=1#L1992-L2045), [plugins.py L81-102](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/plugins.py#L81-L102)):
- User: `${XDG_CONFIG_HOME}/yt-dlp/plugins/<pkg>/yt_dlp_plugins/`, `${XDG_CONFIG_HOME}/yt-dlp-plugins/<pkg>/…`, `~/.yt-dlp/plugins/<pkg>/…`, `~/yt-dlp-plugins/<pkg>/…`.
- System: `/etc/yt-dlp/plugins/<pkg>/yt_dlp_plugins/`, `/etc/yt-dlp-plugins/<pkg>/yt_dlp_plugins/`.
- Executable dir: `<dir-of-binary>/yt-dlp-plugins/<pkg>/yt_dlp_plugins/`.
- Archives: `.zip`/`.egg`/`.whl` with `yt_dlp_plugins/` at the root are accepted in place of `<pkg>/` (e.g. `/etc/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip`).
- `PYTHONPATH` works for non-PyInstaller installs only. `YTDLP_NO_PLUGINS=1` disables plugins.
- `Plugin directories: none` in `-v` means no plugin dirs were found.

**Cache** ([cache.py L17-22](https://github.com/yt-dlp/yt-dlp/blob/bbc809a1161d3bfca51fa36f59dda35556ee85a0/yt_dlp/cache.py#L17-L22)): `--cache-dir`, else `${XDG_CACHE_HOME:-~/.cache}/yt-dlp`, else disabled via `--no-cache-dir`. For the n8n `node` user (uid 1000, `HOME=/home/node`, verified) this is `/home/node/.cache/yt-dlp`. It holds EJS scripts from `ejs:github` (`challenge-solver/`) and other extractor caches. `/home/node/.cache` did **not** exist in the probe container and was not created by the `--simulate` run, so writability under a read-only or volume layout remains to be checked.

## Dependency matrix

| Dependency | Purpose | YouTube class | (a) Alpine/musl + apk | (b) Debian/glibc + apt | (c) No package manager (copy-in) |
|---|---|---|---|---|---|
| yt-dlp **nightly** | Core | Required | `yt-dlp_musllinux[_aarch64]` by tag + sha256 (or zipimport + `python3`, or venv `pip ==<ver>.dev0`). Not `apk yt-dlp` (stable). | `yt-dlp_linux[_aarch64]` by tag + sha256 (or zipimport + `python3` 3.13, or venv pip). Not `apt yt-dlp` (2025.04.30). | PyInstaller binary matching the libc |
| Python ≥ 3.10 | Interpreter | Required | Bundled in the PyInstaller binary; else `python3` 3.14.7 | Bundled; else `python3` 3.13.5 | Bundled (PyInstaller only) |
| yt-dlp-ejs 0.8.0 | Challenge-solver scripts | Required (full support) | Bundled (PyInstaller and zipimport); `apk yt-dlp-ejs` 0.8.0-r1; pip `[default]`/`[pin]` | Bundled; pip `[default]` (no apt pkg) | Bundled |
| JS runtime | Runs EJS | Required (full support) | Base image `node` (n8n: 26.7.0) + `/etc/yt-dlp.conf` `--js-runtimes node`; or `apk deno` 2.7.4 (on by default), `nodejs` 24.18.1, `nodejs-current` 26.5.1 | apt `nodejs` 20 too old. Use official Deno `*-linux-gnu.zip` (2.9.6), apt `quickjs` 2025.04.26, or external Node ≥ 22. | Existing node + config; or Deno gnu zip (glibc only); on musl copy Alpine deno + libs |
| ffmpeg + ffprobe | Merge, post-process | Required in practice | `apk ffmpeg` 8.1.2 (FFmpeg-Builds do **not** run on musl) or a static third-party build | FFmpeg-Builds `ffmpeg-N-…-linux64/linuxarm64-gpl.tar.xz` by `autobuild-*` tag + sha256 (glibc ≥ 2.28), or `apt ffmpeg` 7.1.5 | glibc: FFmpeg-Builds. musl: fully static build, or Alpine ffmpeg + full `.so` closure. |
| CA certificates | TLS | Required | certifi bundled in the binary; `ca-certificates` for system tools | certifi bundled; `ca-certificates` | certifi bundled in the binary |
| certifi, brotli, websockets, requests/urllib3, mutagen, pycryptodomex | Networking, metadata, crypto | Recommended | Bundled; or `py3-*` apk (apk yt-dlp omits requests/certifi) | Bundled; or `python3-*` apt | Bundled |
| curl_cffi | TLS impersonation | Situational | Bundled; not in Alpine; pip musllinux wheel | Bundled; pip | Bundled |
| secretstorage | `--cookies-from-browser` keyring | Not relevant | Bundled | Bundled | Bundled |
| Writable exec temp dir | PyInstaller onefile extraction | Required for onefile binaries | `/tmp` (1777, exec), or use `.zip` onedir | Same | Same |
| Writable cache dir | EJS/player caches | Recommended | `/home/node/.cache/yt-dlp` or `--cache-dir` in config | Same | Same |
| PO token provider | PO tokens (`mweb`/`web` GVS) | Situational | Plugin zip in `/etc/yt-dlp/plugins/` + separate `bgutil` HTTP server container (or script: Node ≥ 20 + npm build) | Same (pip plugin if yt-dlp is pip-installed) | Plugin zip + external provider service |
| Cookies file | Account-gated content, flagged IPs | Situational | `--cookies /path` on a mounted volume (ban risk) | Same | Same |

## Empirical checks

Host: x86_64. `$DL` below is a local scratch download directory. All containers ran with `--rm`; no containers from this work remain.

### E1. Download, checksum and GPG (host)

```sh
B=https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/2026.08.30.232658
for f in yt-dlp yt-dlp_musllinux yt-dlp_linux SHA2-256SUMS SHA2-256SUMS.sig SHA2-512SUMS SHA2-512SUMS.sig; do curl -sSfL -o $f $B/$f; done
sha256sum --ignore-missing -c SHA2-256SUMS; sha512sum --ignore-missing -c SHA2-512SUMS
export GNUPGHOME=$(mktemp -d); curl -sSfL https://github.com/yt-dlp/yt-dlp/raw/master/public.key | gpg -q --import
gpg --verify SHA2-256SUMS.sig SHA2-256SUMS; gpg --verify SHA2-512SUMS.sig SHA2-512SUMS
file yt-dlp yt-dlp_musllinux yt-dlp_linux
```
```
yt-dlp: OK
yt-dlp_linux: OK
yt-dlp_musllinux: OK            (x2: sha256 and sha512)
gpg: Signature made Mon 31 Aug 2026 02:30:01 AM +03
gpg:                using RSA key AC0CBBE6848D6A873464AF4E57CF65933B5A7581
gpg: Good signature from "Simon Sawicki (yt-dlp signing key) <contact@grub4k.xyz>" [unknown]
Primary key fingerprint: AC0C BBE6 848D 6A87 3464  AF4E 57CF 6593 3B5A 7581
yt-dlp:           a /usr/bin/env python3 script executable (Zip archive)
yt-dlp_musllinux: ELF 64-bit LSB executable, x86-64, ... interpreter /lib/ld-musl-x86_64.so.1, stripped
yt-dlp_linux:     ELF 64-bit LSB executable, x86-64, ... interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0, stripped
```

### E2. Release attestation and immutability

```sh
gh api repos/yt-dlp/yt-dlp-nightly-builds/attestations/sha256:39973a5d585e84ca2bf715b029e7ca2b57a63ee428b219b4fe485b2f7ab58e40
gh api repos/yt-dlp/yt-dlp/attestations/sha256:39973a5d585e84ca2bf715b029e7ca2b57a63ee428b219b4fe485b2f7ab58e40
gh api repos/yt-dlp/yt-dlp-nightly-builds/releases/latest --jq '{immutable, tag_name}'
```
```
{"attestations":[{"repository_id":606935641,...,"initiator":"github","bundle":{"mediaType":"application/vnd.dev.sigstore.bundle.v0.3+json", ...
  decoded payload: predicateType "https://in-toto.io/attestation/release/v0.2",
  subject: pkg:github/yt-dlp/yt-dlp-nightly-builds@2026.08.30.232658 + {name, sha256} for all 23 assets;
  certificate SAN https://dotcom.releases.github.com
gh: Not Found (HTTP 404)                    <- yt-dlp/yt-dlp: no build-provenance attestation
{"immutable":true,"tag_name":"2026.08.30.232658"}
```
`gh release verify` / `gh release verify-asset` → `unknown command` (local gh 2.46.0).

### E3. n8n image as root: in-image download and verify, `-v` headers, glibc ffmpeg

```sh
docker run --rm --entrypoint sh --user root -v $DL/ffmpeg-master-latest-linux64-gpl/bin:/ffbin:ro n8nio/n8n:latest -c '
cd /tmp && B=https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/2026.08.30.232658
wget -q "$B/yt-dlp_musllinux" "$B/SHA2-256SUMS" && grep " yt-dlp_musllinux$" SHA2-256SUMS | sha256sum -c - && install -m 0755 yt-dlp_musllinux /usr/local/bin/yt-dlp
/lib/ld-musl-x86_64.so.1 2>&1 | head -2; yt-dlp --version; yt-dlp -v 2>&1
yt-dlp -v --js-runtimes node 2>&1 | grep -E "JS runtimes"; /ffbin/ffmpeg -version 2>&1 | head -2'
```
```
yt-dlp_musllinux: OK
musl libc (x86_64)
Version 1.2.6
2026.08.30.232658
[debug] Command-line config: ['-v']
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds (musllinux_exe)
[debug] Python 3.14.7 (CPython x86_64 64bit) - Linux-7.0.0-31-generic-x86_64-with-musl1 (OpenSSL 3.5.8 25 Aug 2026, musl 1)
[debug] exe versions: none
[debug] Optional libraries: Cryptodome-3.23.0, brotli-1.2.0, certifi-2026.07.22, curl_cffi-0.16.0, mutagen-1.48.1, requests-2.34.2, secretstorage-3.5.0, sqlite3-3.53.4, urllib3-2.7.0, websockets-17.0.1, yt_dlp_ejs-0.8.0
[debug] JS runtimes: none
[debug] Request Handlers: urllib, requests, websockets, curl_cffi
[debug] Plugin directories: none
[debug] Loaded 1745 extractors
yt-dlp: error: You must provide at least one URL.
[debug] JS runtimes: node-26.7.0                       <- with --js-runtimes node
Error loading shared library libmvec.so.1: No such file or directory (needed by /ffbin/ffmpeg)
Error relocating /ffbin/ffmpeg: fcntl64: symbol not found
```

Image facts from the same session:
- Labels: `org.opencontainers.image.version=2.38.6`, `com.docker.dhi.version=26.7.0-alpine3.24-dev`; `User=node`.
- `which` found `/usr/local/bin/node`, `/usr/bin/wget`, `/usr/bin/sha256sum`, `/bin/tar`, `/usr/bin/unzip`.
- `apk: not found`; no `/etc/alpine-release`.

### E4. alpine:3, node:24-alpine, node:22-alpine (host-downloaded binary mounted)

```sh
docker run --rm -v $DL:/dl:ro alpine:3 sh -c '/dl/yt-dlp_musllinux -v 2>&1 | grep -E "yt-dlp version|Python|JS runtimes"; /dl/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg -version 2>&1 | head -1; apk add -q gcompat && /dl/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg -hide_banner -version 2>&1 | head -2'
docker run --rm -v $DL:/dl:ro node:24-alpine sh -c 'node --version; /dl/yt-dlp_musllinux -v --js-runtimes node 2>&1 | grep "JS runtimes"; /dl/yt-dlp_musllinux -v 2>&1 | grep "JS runtimes"; /dl/yt-dlp_musllinux -v --no-js-runtimes 2>&1 | grep "JS runtimes"'
docker run --rm -v $DL:/dl:ro node:22-alpine sh -c 'node --version; /dl/yt-dlp_musllinux -v --js-runtimes node 2>&1 | grep "JS runtimes"'
```
```
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds (musllinux_exe)
[debug] JS runtimes: none
sh: /dl/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg: not found
Error loading shared library libmvec.so.1: No such file or directory (needed by .../ffmpeg)     <- with gcompat
Error loading shared library libgcc_s.so.1: No such file or directory (needed by .../ffmpeg)
v24.21.0
[debug] JS runtimes: node-24.21.0
[debug] JS runtimes: none              <- default (deno only, not installed)
[debug] JS runtimes: none (disabled)   <- --no-js-runtimes
v22.23.2
[debug] JS runtimes: node-22.23.2
```

### E5. debian:stable-slim (trixie): glibc binary + FFmpeg-Builds, musl binary, zipimport

```sh
docker run --rm -v $DL:/dl:ro debian:stable-slim sh -c '
export PATH=/dl/ffmpeg-master-latest-linux64-gpl/bin:$PATH; /dl/yt-dlp_linux -v 2>&1 | grep -E "yt-dlp version|Python|exe versions|Optional|JS runtimes"
/dl/yt-dlp_musllinux --version 2>&1 | head -1
apt-get update -qq && apt-get install -qq -y --no-install-recommends python3; /dl/yt-dlp -v 2>&1 | grep -E "yt-dlp version|Python|Optional|JS runtimes"'
```
```
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds (linux_exe)
[debug] Python 3.14.7 (CPython x86_64 64bit) - Linux-...-with-glibc2.41 (OpenSSL 3.5.8 25 Aug 2026, glibc 2.41)
[debug] exe versions: ffmpeg N-126435-gf93cd72dde-20260906 (setts), ffprobe N-126435-gf93cd72dde-20260906
[debug] Optional libraries: Cryptodome-3.23.0, brotli-1.2.0, certifi-2026.07.22, curl_cffi-0.16.0, mutagen-1.48.1, requests-2.34.2, secretstorage-3.5.0, sqlite3-3.53.4, urllib3-2.7.0, websockets-17.0.1, yt_dlp_ejs-0.8.0
[debug] JS runtimes: none
sh: 3: /dl/yt-dlp_musllinux: not found
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds [bbc809a11] (zip)
[debug] Python 3.13.5 (CPython x86_64 64bit) - Linux-...-with-glibc2.41 (OpenSSL 3.5.6 7 Apr 2026, glibc 2.41)
[debug] Optional libraries: sqlite3-3.46.1, yt_dlp_ejs-0.8.0
[debug] JS runtimes: none
```

### E6. Alpine `apk add yt-dlp deno`, and venv pip nightly pin

```sh
docker run --rm alpine:3 sh -c 'apk add -q --no-cache yt-dlp deno; yt-dlp -v 2>&1 | grep -E "yt-dlp version|exe versions|Optional|JS runtimes"; apk info -L yt-dlp-ejs | head -3; ldd /usr/bin/deno | head -3; du -sh /usr/bin/deno /usr/lib/python3.14'
docker run --rm alpine:3 sh -c 'apk add -q --no-cache python3; python3 -m venv /opt/yt-dlp && /opt/yt-dlp/bin/pip install -q "yt-dlp[default,curl-cffi]==2026.8.30.232658.dev0"; /opt/yt-dlp/bin/pip freeze; du -sh /opt/yt-dlp; /opt/yt-dlp/bin/yt-dlp -v 2>&1 | grep -E "yt-dlp version|Optional|JS runtimes"'
```
```
[debug] yt-dlp version stable@2026.08.19 from yt-dlp/yt-dlp [594bd50c2]
[debug] exe versions: ffmpeg 8.1.2 (setts), ffprobe 8.1.2
[debug] Optional libraries: Cryptodome-3.23.0, brotli-1.2.0, mutagen-1.47.0, secretstorage-3.5.0, sqlite3-3.53.4, websockets-16.0, yt_dlp_ejs-0.8.0
[debug] JS runtimes: deno-2.7.4
usr/lib/python3.14/site-packages/yt_dlp_ejs/__init__.py
	/lib/ld-musl-x86_64.so.1 (0x...)
	libzstd.so.1 => /usr/lib/libzstd.so.1
105.3M	/usr/bin/deno
72.7M	/usr/lib/python3.14
---
brotli==1.2.0  certifi==2026.7.22  cffi==2.1.1  charset-normalizer==3.5.1  curl_cffi==0.16.3  idna==3.19
mutagen==1.48.1  pycparser==3.0  pycryptodomex==3.23.0  requests==2.34.2  urllib3==2.7.0  websockets==17.1
yt-dlp==2026.8.30.232658.dev0  yt-dlp-ejs==0.8.0
98.8M	/opt/yt-dlp
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds [bbc809a11] (pip)
[debug] Optional libraries: Cryptodome-3.23.0, brotli-1.2.0, certifi-2026.07.22, curl_cffi-0.16.3, mutagen-1.48.1, requests-2.34.2, sqlite3-3.53.4, urllib3-2.7.0, websockets-17.1, yt_dlp_ejs-0.8.0
[debug] JS runtimes: none
```

### E7. FFmpeg-Builds tarball (host; `latest` as of 2026-09-06 build)

```sh
curl -sSfL -o checksums.sha256 https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/checksums.sha256
curl -sSfL -o ffmpeg-master-latest-linux64-gpl.tar.xz https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
sha256sum --ignore-missing -c checksums.sha256 && tar -xJf ffmpeg-master-latest-linux64-gpl.tar.xz
file ffmpeg-master-latest-linux64-gpl/bin/*; strings .../bin/ffmpeg | grep -o '^GLIBC_[0-9.]*' | sort -uV | tail -1
```
```
ffmpeg-master-latest-linux64-gpl.tar.xz: OK
ffmpeg:  ELF 64-bit LSB pie executable, x86-64, version 1 (GNU/Linux), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 4.18.20, stripped
141M ffmpeg / 140M ffprobe / 142M ffplay
ffmpeg version N-126435-gf93cd72dde-20260906 ... built with gcc 15.2.0 (crosstool-NG 1.28.0.23_185f348)
configuration: ... --cross-prefix=x86_64-ffbuild-linux-gnu- ... --enable-gpl --enable-version3 ...
GLIBC_2.28
```
(`latest` was replaced by the 2026-09-10 22:10 build before 2026-09-11; checksums differ now.)

### E8. The one YouTube metadata probe (n8n image, default `node` user, Node via system config)

```sh
printf -- '--js-runtimes node\n' > yt-dlp.conf
docker run --rm --entrypoint sh -v $DL/yt-dlp_musllinux:/usr/local/bin/yt-dlp:ro -v $PWD/yt-dlp.conf:/etc/yt-dlp.conf:ro n8nio/n8n:latest \
  -c 'id; echo HOME=$HOME; cd /tmp; timeout 120 yt-dlp -v --simulate "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>&1; echo "exit=$?"; find $HOME/.cache -maxdepth 3 2>/dev/null | head'
```
```
uid=1000(node) gid=1000(node) groups=1000(node),1000(node)
HOME=/home/node
[debug] System config "/etc/yt-dlp.conf": ['--js-runtimes', 'node']
[debug] yt-dlp version nightly@2026.08.30.232658 from yt-dlp/yt-dlp-nightly-builds (musllinux_exe)
[debug] exe versions: none
[debug] JS runtimes: node-26.7.0
[debug] [youtube] [pot] PO Token Providers: none
[debug] [youtube] [jsc] JS Challenge Providers: bun (unavailable), deno (unavailable), node, quickjs (unavailable)
[youtube] Extracting URL: https://www.youtube.com/watch?v=jNQXAC9IVRw
[youtube] jNQXAC9IVRw: Downloading webpage
[debug] [youtube] Forcing "main" player JS variant for player 8c3fda2d
[youtube] jNQXAC9IVRw: Downloading visionos player API JSON
[youtube] jNQXAC9IVRw: Downloading m3u8 information
[debug] Default format spec: best/bestvideo+bestaudio
[info] jNQXAC9IVRw: Downloading 1 format(s): 395+251
exit=0
(no ~/.cache entries)
```

What the probe showed:
- No bot check or 403.
- No `Solving JS challenges using node` line, so the Node EJS path was **not** exercised for this video/client combination.
- `Default format spec: best/bestvideo+bestaudio` reflects the missing ffmpeg. The chosen `395+251` is separate video+audio, which a real download would have to merge with ffmpeg.
- The host's IP type (residential vs datacenter) is not representative of deployment.

## Conflicts / uncertainties

1. **Deno minimum.** The runtime check and wiki say `2.3.0`, but pyproject's `deno` extra requires `deno>=2.6.6` (`pin-deno` = 2.9.5). The extra governs only the PyPI `deno` wheel; the runtime accepts ≥ 2.3.0.
2. **FFmpeg-Builds "static" wording.** The README title says "Static Auto-Builds" and mentions release/7.1 builds. In fact only master GPL builds are published, and Linux binaries link glibc dynamically (≥ 2.28 by symbol versions, x86_64 only checked). They are unusable on musl without a full glibc graft.
3. **FFmpeg-Builds mutability.** `latest` is mutable (`immutable: false`) and changed during this research (2026-09-06 → 2026-09-10 build), so pin an `autobuild-*` tag. Retention: on 2026-09-11 the repo held 37 releases (`latest` + 36 `autobuild-*`). The oldest is `autobuild-2024-10-31-14-17` and the next is `autobuild-2024-11-30-14-13`, so older daily builds are pruned and only a sparse subset survives. The policy is not documented in the README. Mirror the tarball, or accept that a pinned tag may disappear.
4. **Release attestation verification** was only fetched via REST. `gh release verify` / `verify-asset` were not run (gh 2.46.0 too old). The exact gh version that introduced them was not established.
5. **The probe did not exercise JS challenge solving**, so "Node 26 + EJS 0.8.0 solves challenges in the n8n image" is supported by detection (`JS Challenge Providers: … node`) but not by an observed solve. Datacenter-IP / bot-check behaviour is untested.
6. **`ejs:npm` integrity** — the claim that npm package contents are not hash-verified is inferred from code (`--no-lock`, only the lib script hash is in `_ALLOWED_HASHES`).
7. **Debian ffmpeg 7.1.5 vs 8.0.** yt-dlp says historical patches are unnecessary "as of 8.0"; whether 7.1.x has any practical YouTube issues was not verified.
8. **Nightly cadence.** The README says "shortly before midnight UTC on any day that sees changes", but daytime tags exist (manual dispatch assumed). No nightly since 2026-08-30 because `master` is unchanged (HEAD `bbc809a` on 2026-09-11). One nightly (`2026.08.25.233329`) had 25 assets instead of 23; not investigated.
9. **The `yt-dlp_linux` glibc 2.17 floor** comes from the README and manylinux2014 build image; not tested on an old glibc. Running the glibc binary on musl was not tested.
10. **n8n image facts** (DHI Alpine 3.24, no `apk`, Node 26.7.0) are for `n8nio/n8n:latest` = 2.38.6 as pulled 2026-09-10. The base-image topic is being researched separately and may supersede this.
11. **"Sign in to confirm you're not a bot"**: no first-party yt-dlp wiki section found. Guidance is inferred from the PO Token Guide, Extractors page and FAQ (429 section).
