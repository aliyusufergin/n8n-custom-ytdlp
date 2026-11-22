## Facts

- Route items 1–5 are done and pushed to draft PR #30. CI passes on both images and both
  architectures; publishing itself can only run from `main`.
- The independent check's six findings are fixed (see `done.md`). The commit-lock
  scenarios were checked locally; the publish chain has never run on GitHub.
- **Before or right after the merge, the user needs to:**
  - make sure `DOCKERHUB_TOKEN` can push to a new repository `aliyusufergin/n8n-ytdlp-ai`,
    or create that repository first;
  - add a Docker Hub immutability rule for its build tags, as on the custom image's
    repository.
- The merge publishes the custom image once more (accepted, journal) and the variant for
  the first time.

## Proposal

Milestone: ask the user to merge PR #30 (or approve that I mark it ready and merge). Then
watch the first publish run, and fix anything in the AI chain. Finally, the user checks
"Done means" 2 on their deployment: sign in, recreate the container on a newer tag, and run
both tools from an Execute Command node.
