# Done

- Smoke test (amd64, 2026-11-22): codex 0.171.0 and agy 1.5.14 musl binaries match their GitHub digests and run as `node` in the pinned n8n image. The user signed in once through `docker run -it` (codex device code, agy paste-the-code). A fresh container with only the two volumes kept both sign-ins: codex in `~/.codex/auth.json`, agy in `~/.gemini/antigravity-cli/antigravity-oauth-token` (file, no keyring). arm64 is left to CI (journal).
