## Facts

- The variant is published and verified (see `done.md`). Done-means items 1, 4 and 5 are
  met. The README is on `main`.
- **Open done-means items:**
  - 2: the user signs in on their deployment and the sign-in survives a recreated
    container. Only the user can check this.
  - 3: a codex or agy release publishes only the variant. Wait for the next release
    (codex releases every few days), then compare the variant and custom tags and the lock
    commit.
  - 6: a scheduled run with no upstream change publishes nothing. Check the next quiet
    scheduled run.
- **Pending user actions:**
  - the Docker Hub immutability rule on `n8n-ytdlp-ai` (UI only);
  - deleting the local test volumes `aiv-codex` and `aiv-gemini`, which hold real tokens.
- This record lives on branch `ai-variant-record`, not on `main`. Pushing `.work/` to
  `main` would republish both images (journal).

## Proposal

Once the user has checked done-means 2, confirm items 3 and 6 from the next publish runs,
then run the final independent check and close the work.
