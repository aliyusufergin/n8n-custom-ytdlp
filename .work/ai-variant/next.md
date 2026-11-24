## Facts

- Done-means 1, 2, 4, 5 and 6 are verified (`done.md`).
- Done-means 3 is still open. A run where codex or agy changed but n8n, yt-dlp and ffmpeg
  didn't has not happened yet. So far both tool updates came together with n8n changes
  (`7f8835e`, `58056c4`), and each of those published both images, as designed.
  - yt-dlp nightlies land about once a day and runs come every 6 hours, so most runs see no
    yt-dlp change, and a codex-only run should show up within days.
  - Check: a lock commit whose message has only an "AI variant" part. The custom image's
    `published` and its Docker Hub tags must be unchanged by that run.
- Branch `ai-variant-attestation-retry` adds the retry to `verify-attestation-ai` and
  carries the work record. Merging it publishes both images once (a workflow change is
  not Markdown); the user decides when.
- `.work/` pushes never publish, because every record file is Markdown (journal
  correction).

## Proposal

After the user's merge decision, wait for a codex- or agy-only run to confirm done-means
3. Then run the final independent check and close the work.
