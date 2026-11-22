## Facts

- Nothing is built yet. Branch `ai-variant-groundwork` holds `AGENTS.md` (alice-skills
  flow), `survey.md` and this spec.
- `survey.md` lists release assets, checksum sources, state folders, sign-in flows, flags
  and pitfalls for both tools, with sources checked 2026-11-22. Nothing in it was run:
  the permission classifier blocked running the downloaded binaries in a container during
  the survey. Running upstream binaries locally will need the user's approval.
- The n8n image is Alpine (Docker Hardened Images), Node v26, user `node` (uid 1000),
  HOME=/home/node, no package manager.
- Today one lock (`build-inputs.lock.json`, with a `published` section) drives one build
  tag for the custom image and runners image (`scripts/updater.py`, `scripts/publish.py`,
  `.github/workflows/publish.yml`). The variant must not be coupled to that tag.
- The binaries are large: codex about 315 MB, agy about 245 MB unpacked, per architecture.

## Proposal

Route item 1: the smoke test.

- Inside the pinned n8n image, on amd64 and, through emulation or a runner, on arm64, run:
  - `codex --version`, `codex exec --help`
  - `agy --version`, `agy -p --help`
  - both interactive sign-in flows through `docker exec -it`, up to the point where a URL
    or code is printed.
- Also check whether codex needs `rg`, and which
  folders each tool writes its sign-in state to.

These are the assumptions that would change the design if wrong, so they come before any
pipeline work.
