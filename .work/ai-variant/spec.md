# AI variant: n8n-ytdlp-ai with Codex CLI and Antigravity CLI

## Intent

A second published image, `aliyusufergin/n8n-ytdlp-ai`, for deployments that want n8n
workflows to run AI coding agents. It is the custom image plus OpenAI's Codex CLI (`codex`)
and Google's Antigravity CLI (`agy`). The user signs in once with their own subscriptions
(a ChatGPT plan and a Google account, not API keys). Workflows then run the tools
non-interactively from the Execute Command node, and the sign-in survives every image
update. Like the custom image, it stays current on its own and assumes nothing about a
particular deployment. Background and sources: `survey.md`.

## Commitments

- **The custom image and the companion runners image are untouched.** Their contents,
  tags and publishing are unchanged. A codex or agy release never republishes either of
  them or moves their tags, and a failed variant publish never blocks or undoes theirs.
- **Variant publishing**
  - The variant gets its own Docker Hub repository with the same tag shapes as the custom
    image: `2`, `2.<minor>`, `2.<minor>.<patch>`, plus build tags that are never moved.
  - Every variant publish adds its own build tag and moves the variant's floating tags to it.
  - It is built for linux/amd64 and linux/arm64.
  - It follows n8n's stable track and contains the same yt-dlp nightly and ffmpeg as the
    custom image built from the same lock.
- **Pinned, stable, automatic.** codex and agy are pinned in the lock file by version and
  sha256 like every other build input. Only stable releases are used: GitHub's latest release of each repository, never a
  prerelease. A new stable release of either is published by the scheduled workflow
  without anyone acting.
- **Sign-in persistence**
  - Sign-in state lives in `/home/node/.codex` and `/home/node/.gemini`.
  - The image creates both folders, owned by `node`; deployments mount a separate volume
    on each.
  - The tools can write refreshed tokens there.
  - Nothing is stored in `/home/node/.n8n`.
- **What the image leaves out**
  - No secrets, credentials or tool settings are baked in. Sandbox and approval flags stay
    each workflow's choice.
  - The one exception: agy's self-update is switched off, so the pinned version stays put.
  - Enabling Execute Command stays a deployment setting.
- **The README states plainly** that using a personal Antigravity subscription from n8n
  may breach Google's consumer-plan terms and put the account at risk, and that Google
  Workspace accounts cannot sign in with a subscription.

## Not doing

- A runners twin for the variant.
- Other AI CLIs (Claude Code, Gemini CLI, …).
- Making the tools' own sandboxes work, which would need loosened container security.
- Defaults in `config.toml` or `settings.json`.
- Designing for API-key auth. It may simply work; it is not tested or documented here.
- Sigstore verification of codex: parked as a follow-up.
- A new ADR. Decisions live in this spec and the journal.

## Done means

1. **The variant runs on both architectures.**
   - Setup: anonymously pull `aliyusufergin/n8n-ytdlp-ai:2` on amd64 and on arm64.
   - Check: as user `node`, `codex --version`, `agy --version`, `yt-dlp --version` and
     `ffmpeg -version` all succeed, and `codex exec --help` works too.
   - Also: n8n starts with the upstream container contract.
   - Seen in: the publish workflow's verification jobs.
2. **The sign-in survives an update.**
   - Setup: on a deployment with the two volumes, the user signs in once to each tool
     through `docker exec -it`, following the README.
   - Check: after the container is recreated on a newer variant tag, an Execute Command
     node runs `codex exec …` and `agy -p …` successfully with no new sign-in.
   - Seen by: the user on their own deployment.
3. **Tool updates publish only the variant.**
   - Trigger: a new stable codex or agy release.
   - Check: within the scheduled cycle, a new variant build tag appears with the new
     version in its labels. The custom image's and runners' tags and digests stay where
     they were.
   - Seen in: Docker Hub tag listings and the lock commit.
4. **Variant labels and verification.** It carries all of the custom image's labels, plus
   codex's and agy's versions and digests in the same naming pattern. The README shows its
   verification command for the variant's repository, and that command passes.
   - Seen in: the publish workflow's verification step.
5. **The README documents the variant for any deployment:**
   - what it adds;
   - the Compose volume lines, including `chown 1000:1000` for bind mounts;
   - the one-time sign-in steps and their prerequisites (ChatGPT device-code setting,
     personal Google account);
   - a working example of the flags that run each tool non-interactively in a container,
     shown as an example and not baked in;
   - a pointer to the existing section on enabling Execute Command;
   - the Antigravity terms risk.
6. **Nothing regresses.** The existing test suites pass, and a scheduled run with no
   upstream change publishes nothing.

## Assumptions

- **Sources and checksums.** Both tools come from their GitHub releases:
  - codex: `rust-vX.Y.Z` tags, asset `codex-<arch>-unknown-linux-musl.tar.gz`;
  - agy: `google-antigravity/antigravity-cli`, asset `agy_cli_linux_<arch>_musl.tar.gz`.
  - Checksums come from the GitHub API asset `digest`.
- **Both static binaries run as `node` on the n8n image (Alpine/musl).** Confirmed
  for codex 0.171.0 and agy 1.5.14 on amd64 and arm64 (CI, PR #30).
  - Nothing beyond what that image ships is needed.
  - codex's standalone binary needs no external `rg`.
- **Sign-in flows.** Confirmed on amd64 on 2026-11-22 through `docker run -it`:
  - `codex login --device-auth` works once device codes are enabled in ChatGPT's settings;
  - agy's paste-the-code flow works without SSH;
  - both sign-ins survive in a new container that has only the two volumes.
- **Workflow flags.** In a container, workflows run `codex exec --sandbox
  danger-full-access --skip-git-repo-check` and `agy -p --dangerously-skip-permissions`.
- **Self-update.** `AGY_CLI_DISABLE_AUTO_UPDATE=true` switches agy's self-update off.
- **Volume ownership.** A fresh named volume takes its ownership from the image folder.
- **Repository and credentials.** The Docker Hub repository may need to be created by the
  user, and the existing publishing token may need access to it.

## Route

1. **Smoke test.** Run both binaries, `codex exec`, `agy -p` and both sign-in flows inside
   the real n8n image on amd64 and arm64, and note where each tool writes its sign-in
   state. This tests the riskiest assumptions; a failure
   changes the design.
   - MILESTONE if any of them fails.
2. **Updater and lock.** Lock entries for codex and agy, with stable-only detection. The
   variant's own published state and build tag sit beside the custom image's.
3. **Build and tests.** The variant build, and its image acceptance tests.
4. **Publishing.** The variant goes through the workflow independently of the custom
   image: publish, verify, attest, and the lock commit. This may need the user to set up
   the Docker Hub repository or token.
5. **Documentation.** README sections, and a glossary entry in `CONTEXT.md`.
6. **MILESTONE: first published variant.** The user signs in on their deployment,
   recreates the container and confirms "Done means" 2.
