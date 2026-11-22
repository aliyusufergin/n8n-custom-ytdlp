# Journal

- 2026-11-22: The user accepted that merging this work to main may republish the custom and runners images once (pushes to main publish today). The "never republishes" commitment covers codex and agy releases only.
- 2026-11-22: arm64 can't run locally (no binfmt/qemu), so arm64 is first checked by the CI acceptance tests (route 3), not by the smoke test.
- 2026-11-22: No external `rg` for codex. Its shell tool falls back to the image's busybox grep/find; revisit only if a workflow shows it matters.
- 2026-11-22: A named volume mounted on a folder the image lacks is root-owned, so `node` can't write it. This confirms the image must pre-create `/home/node/.codex` and `/home/node/.gemini` owned by `node`.
- 2026-11-22: agy also keeps conversations, caches and logs under `~/.gemini` (about 2 MB after one prompt), so that volume grows with use. That is acceptable; the README should mention it.
