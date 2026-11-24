# Parked ideas

- **Sigstore verification for codex** (from the AI variant, 2026-11-22). codex release
  assets ship `.sigstore` bundles; the updater could verify them the way it verifies
  yt-dlp's signature. Today codex is pinned by the GitHub asset digest only.
- **Ignore `.work/` in publish pushes** (from the AI variant, 2026-11-22). Add `.work/**` to `paths-ignore` in `.github/workflows/publish.yml` with the next real change to `main`, then merge branch `ai-variant-record` (or its record files) along with it.
