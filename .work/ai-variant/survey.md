# Survey: AI variant image with Codex CLI and Antigravity CLI

Surveyed 2026-11-22. Nothing below was run inside the n8n image yet: every runtime claim
is from docs, release APIs and static inspection of the binaries.

## Intent

- Publish a separate variant `aliyusufergin/n8n-ytdlp-ai`: everything in the custom image
  plus OpenAI Codex CLI (`codex`) and Google Antigravity CLI (`agy`). Same tag scheme,
  linux/amd64 + linux/arm64, n8n stable track, every input pinned by version + sha256 in
  the lock file, republished automatically when an input changes. Stable releases only.
- The custom image `n8n-ytdlp` and the companion runners image stay unchanged; no runners
  twin for the variant.
- Auth is the user's subscription (ChatGPT plan, Google account), not API keys. Login
  happens once, headless, through `docker exec -it`, and survives container recreation.
- The image pre-creates the tools' state folders owned by `node`; deployments mount a
  separate volume for each. Not inside `/home/node/.n8n`.
- Workflows run the tools non-interactively from the Execute Command node, which stays a
  deployment setting (ADR 0001).

## Bottom line

The plan holds. Both tools ship static musl binaries for both architectures on GitHub
Releases with stable tags and sha256 digests. Both fall back to plain files for login state
when no keyring exists. So they fit the existing "single file, no runtime, pinned by
checksum" pattern and the "separate volumes" decision. What changes:

1. **Antigravity's terms are the real risk.** Its FAQ says `agy -p` is for "direct
   scripting and CI", but "wrapping `agy` inside third-party … applications" is not
   supported under consumer plans, and third-party use of the login can suspend the
   account. Calling it from n8n may fall on either side. Codex has no such prohibition: it
   documents ChatGPT login for automation as an "advanced" option for trusted runners.
2. **The variant is large.** codex is about 315 MB and agy about 245 MB unpacked, so each
   build adds roughly 560 MB per architecture. Acceptable for an opt-in variant, and it
   confirms keeping the custom image without them.
3. **The variant must not drag the custom image along.** Today one lock publishes the
   custom and runners images under one build tag. Codex and agy each release stable
   versions every few days, so the variant needs its own build tag and its own "what
   changed" decision. Otherwise the custom image and runners image would be republished,
   and Dockhand would update every deployment, for changes they don't contain.
4. **Neither tool's sandbox works in an ordinary container.** They need unprivileged user
   namespaces, which Docker blocks. The container is the isolation, so workflows pass
   `codex exec --sandbox danger-full-access --skip-git-repo-check` and
   `agy -p --dangerously-skip-permissions` (or scoped `permissions.allow` rules).
5. **Login has two prerequisites the README must spell out.**
   - Codex device-code login (`codex login --device-auth`) only works after it is enabled
     in ChatGPT's security settings, or by the workspace admin.
   - Antigravity login does not work with Google Workspace accounts on a subscription;
     only personal Free, Pro and Ultra accounts.
6. **The first ticket should be a smoke test.** Run both binaries, and both login flows
   through `docker exec -it`, in the real n8n image on both architectures. Two things are
   untested and could change the design:
   - agy's paste-the-code login is documented for SSH. Its behaviour under `docker exec`
     is not documented.
   - codex on Alpine arm64 has an open TUI crash. The `exec` path is not reported broken.

## Options

**Codex source**
- Standalone `codex-<arch>-unknown-linux-musl.tar.gz` from `openai/codex` releases. One
  static binary. Checksum from the GitHub API asset `digest`, plus a sigstore bundle.
  *Recommended.*
- `codex-package-<arch>.tar.gz`. Covered by `codex-package_SHA256SUMS` and bundles `rg`
  and `bwrap`. But its arm64 `rg` is glibc-linked (issue #52578) and won't run on Alpine,
  and `bwrap` is useless without user namespaces.

**Antigravity source**
- `agy_cli_linux_{x64,arm64}_musl.tar.gz` from GitHub `google-antigravity/antigravity-cli`
  releases. sha256 from the API asset `digest`. No signatures exist. Poll
  `/releases/latest`; none of the 95 releases is a prerelease. *Recommended.*
- The GCS manifest service that `install.sh` uses (sha512, versioned URLs). Undocumented
  Cloud Run endpoint, so worse for an updater.

**Verification depth**
- codex: verify the sigstore bundle in the updater, as yt-dlp's signature is verified
  today. Stronger, but adds tooling.
- agy: digest only; there is nothing else.

## Pitfalls

- **Codex**
  - Stable tags are `rust-vX.Y.Z`. Several alphas a day carry `prerelease: true`, so match
    `^rust-v\d+\.\d+\.\d+$` and `prerelease == false`.
  - Each tarball holds `codex-<target>`, which must be renamed to `codex`.
  - A plan change makes a stored ChatGPT login fail with 401 (#47456). The fix is to log in
    again; the README should say so.
- **agy**
  - It self-updates in the background. Set `AGY_CLI_DISABLE_AUTO_UPDATE=true` in the image
    so the pinned version stays put and no lock or warning noise appears. The binary is
    root-owned, so it can't be overwritten anyway.
  - The tarball's binary is named `antigravity`. Install it as `/usr/local/bin/agy`.
  - `agy -p` defaults to Auto mode, which needs the sandbox. In Docker it drops to default
    mode and refuses approval-needing actions unless permissions are granted.
  - Runs without a terminal and without a stored login fail fast with
    `authentication required` (exit code 3 plus an `AGY_ERROR` JSON line).
  - Telemetry opt-out is an account setting, not an environment variable.
- **Shared**
  - `rg`: agy bundles it. Whether codex's standalone binary needs an external `rg` for
    file search is unverified; check it in the smoke test.
  - Both write refreshed tokens back, so the volumes must be writable by uid 1000. A fresh
    named volume copies ownership from the image folder; a bind mount does not, so the
    README must say it needs `chown 1000:1000`.
  - Tokens are passwords: `auth.json` under `~/.codex`, and file storage under
    `~/.gemini`.

## Decisions this opens

Resolved by the user on 2026-11-22: 1–4 as recommended. 6: record the variant's decisions in
the spec, not as an ADR; the user has moved from the ADR-based skill set to alice-skills.


1. **Ship agy despite the consumer-plan terms?** *Recommendation:* ship it. The README
   states plainly that using a personal Antigravity subscription from n8n may count as
   "wrapping in a third-party application" and risks the account, and that Workspace
   accounts are unsupported. This is the user's risk to accept; if not, the variant is
   Codex only.
2. **Build tag and publishing for the variant.** *Recommendation:* the variant gets its own
   lock section and its own build tag. It is published when its own inputs change: n8n,
   yt-dlp, ffmpeg, codex or agy. The custom and runners images are published only when
   their own inputs change. Same tag shapes (`2`, `2.39`, `2.39.8`, build tag) in the new
   repository.
3. **Folders and environment variables the image sets.** *Recommendation:*
   - Pre-create `/home/node/.codex` and `/home/node/.gemini`, owned by `node`.
   - Set `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
   - Ship no `config.toml` or `settings.json` defaults: sandbox and approval flags stay each
     workflow's choice, like yt-dlp options. The README shows the flags.
   - Don't relocate state with `CODEX_HOME` or the undocumented `ANTIGRAVITY_CONFIG_REL_DIR`.
4. **Codex signature verification.** *Recommendation:* digest pinning now, sigstore
   verification as a follow-up ticket.
5. **External ripgrep.** *Recommendation:* add none unless the smoke test shows codex
   needs it.
6. **A new ADR** recording "the variant exists, is separate, and holds subscription logins
   in deployment volumes". *Recommendation:* yes; it reverses the README's "no other
   tools" stance for one variant.

## Sources

All fetched 2026-11-22.

- **Codex**
  - Releases: `gh api repos/openai/codex/releases` (latest stable rust-v0.171.0,
    2026-11-20).
  - Auth: https://learn.chatgpt.com/docs/auth (undated; developers.openai.com/codex/auth
    redirects there).
  - Non-interactive mode and sandboxing: https://learn.chatgpt.com/docs/non-interactive-mode,
    https://learn.chatgpt.com/docs/sandboxing (undated).
  - Credential store default: `codex-rs/config/src/types.rs` on main.
  - Issues on https://github.com/openai/codex: #52578 (2026-10-09), #58698 (2026-11-01),
    #9418 (2026-01-17), #16211 (2026-03-30), #12247 (2026-02), #29186 (2026-06),
    #47456 (2026-09).
  - Usage limits: https://help.openai.com/en/articles/11369540
- **Antigravity**
  - Install script: https://antigravity.google/cli/install.sh (last-modified 2026-11-21).
  - Releases: https://github.com/google-antigravity/antigravity-cli (1.0.4, 2026-06-01, to
    1.5.14, 2026-11-21).
  - Docs: https://antigravity.google/docs/install (2026-11-21),
    https://antigravity.google/docs/cli/headless, https://antigravity.google/docs/cli/reference,
    https://antigravity.google/docs/cli/troubleshooting, https://antigravity.google/docs/faq,
    https://antigravity.google/docs/plans (2026-11-21).
- **Project:** `scripts/updater.py`, `scripts/publish.py`,
  `.github/workflows/publish.yml`, and the n8n image (Alpine, Node v26, uid 1000,
  HOME=/home/node).
