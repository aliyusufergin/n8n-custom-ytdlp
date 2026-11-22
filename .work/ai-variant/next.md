## Facts

- Route items 1–4 are implemented. Publishing (item 4) has only been checked locally:
  - actionlint is clean apart from the existing `queue: max`, which actionlint 1.7.7
    doesn't know;
  - `commit_lock.py` passed the custom-only, AI-only and both scenarios in a throwaway git
    repo.
- The variant's real publish path (Docker Hub push to `aliyusufergin/n8n-ytdlp-ai`,
  attestation, verification) first runs after the merge to main. That push also republishes
  the custom image once, which the user accepted (journal).
- The Docker Hub repository `aliyusufergin/n8n-ytdlp-ai` doesn't exist yet. A personal
  account's push normally creates it, but the `DOCKERHUB_TOKEN` scope is unknown. If the
  first push is refused, the user creates the repository or widens the token.
- PR #30 is a draft. CI on it checks the build-and-test split, not publishing.

## Proposal

Route item 5: documentation.

- README sections for the variant: what it adds; Compose volumes, including `chown` for
  bind mounts; one-time sign-in and its prerequisites; non-interactive flags as an example;
  a pointer to enabling Execute Command; the Antigravity terms risk; the verification
  command for `n8n-ytdlp-ai`; the "no other tools" text adjusted.
- A `CONTEXT.md` glossary entry for the AI variant.
- Then the independent check, and the merge decision with the user before the milestone.
