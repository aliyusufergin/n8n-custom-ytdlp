## Facts

- The automated smoke test passed on amd64 (see `done.md`). Binaries are unpacked at
  `/tmp/claude-1000/-home-dev-projects-n8n-custom-ytdlp/25e08389-100b-4175-8639-8eddec5ae21c/scratchpad/smoke/bin`;
  that folder may be cleared, and re-downloading takes a minute.
- **Untested:** a completed sign-in, and whether the credentials land inside `~/.codex` and
  `~/.gemini` and survive a new container. The user was asked to run a manual sign-in test
  with two test volumes, `aiv-codex` and `aiv-gemini`. After they report back:
  - list the file *names* in both volumes (never print their contents);
  - record the result in `done.md` and the spec's assumptions.
- If credentials land elsewhere, or the keyring is used, stop: the volume layout in the
  commitments would need the user's approval to change.
- Nothing in the repository's build or publishing has changed yet.

## Proposal

Once the sign-in test confirms the folders, do route item 2: lock entries and updater
detection for codex and agy, plus the variant's own published state and build tag. It is
the foundation that the build and publishing steps rest on.
