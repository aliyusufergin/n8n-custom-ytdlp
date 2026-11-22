## Facts

- Route items 1 (smoke test) and 2 (updater and lock) are done; see `done.md` and the journal.
- `python3 tests/test_updater.py` passes 39 tests offline.
- The plan is backward compatible. Its custom-image keys are unchanged, and the new
  `ai_variant` object holds the variant's `build`, `reason`, `change_summary`, `build_tag`,
  `floating_tags`, `error` and `build_inputs`.
- If this branch merged as-is, the custom pipeline would keep working and would only start
  carrying `codex` and `agy` in the lock. Nothing reads `ai_variant` yet.
- The branch is rebased on `origin/main` (2.48.7). Local `main` had been two months
  behind; see the knowledge file.
- arm64 runs of codex and agy are still unverified. CI is the first place they run.

## Proposal

Route item 3: the variant's build and its image acceptance tests.

- A Dockerfile target that adds codex and agy on top of the custom image's stage,
  verifying each against the lock's sha256.
- The `node`-owned `/home/node/.codex` and `/home/node/.gemini` folders,
  `AGY_CLI_DISABLE_AUTO_UPDATE`, and the variant's labels.
- Extending `scripts/build_and_test.py` and `tests/test_image.py` so both images are
  built and checked on amd64 and arm64 in CI.

This is where the arm64 assumption first gets tested.
