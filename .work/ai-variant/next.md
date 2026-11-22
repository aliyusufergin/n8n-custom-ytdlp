## Facts

- Route items 1–3 are done for amd64; see `done.md`.
- **arm64 is unverified.** This machine can't run arm64. CI's `Build and test (ai, arm64)`
  job is the first real test. It runs on a pull request (`image.yml`), so the branch must
  be pushed and a PR opened, which needs the user's go-ahead.
- Local check commands:
  - `python3 scripts/build_and_test.py --variant ai` (about 3 minutes; the YouTube warning
    is this machine's Google networking, see knowledge);
  - `python3 scripts/build_and_test.py` for the custom image;
  - `python3 tests/test_updater.py`.
- The publish workflow still publishes only the custom image. A temporary skip in
  `build-and-test.yml` keeps publish runs from building the variant.

## Proposal

1. With the user's go-ahead, push `ai-variant-groundwork` and open a draft PR, so CI checks
   both variants on arm64.
2. Then route item 4: wire the variant into the publish workflow independently of the
   custom image.
