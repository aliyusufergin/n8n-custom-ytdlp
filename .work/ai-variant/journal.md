# Journal

- 2026-11-22: The user accepted that merging this work to main may republish the custom and runners images once (pushes to main publish today). The "never republishes" commitment covers codex and agy releases only.
- 2026-11-22: arm64 can't run locally (no binfmt/qemu), so arm64 is first checked by the CI acceptance tests (route 3), not by the smoke test.
- 2026-11-22: No external `rg` for codex. Its shell tool falls back to the image's busybox grep/find; revisit only if a workflow shows it matters.
- 2026-11-22: A named volume mounted on a folder the image lacks is root-owned, so `node` can't write it. This confirms the image must pre-create `/home/node/.codex` and `/home/node/.gemini` owned by `node`.
- 2026-11-22: agy also keeps conversations, caches and logs under `~/.gemini` (about 2 MB after one prompt), so that volume grows with use. That is acceptable; the README should mention it.
- 2026-11-22: The variant's publish decision compares the current inputs with `published_ai_variant.build_inputs` (all five inputs as last published for the variant), not with the lock's top-level entries. This makes a failed variant publish retry on the next run even after the custom image published the same n8n/yt-dlp/ffmpeg. The lock commit must write `published_ai_variant` only after a verified variant publish.
- 2026-11-22: A codex/agy upstream error never stops the updater: the custom plan is unaffected, the locked tool entries are kept, and `plan.ai_variant.error` is set with `build: false`. Route 4 must fail the variant's job (and so open the failure issue) when that field is set.
- 2026-11-22: The committed lock now carries `codex` and `agy` entries (codex 0.171.0, agy 1.5.14) so local and PR builds of the variant work without a plan. There is no `published_ai_variant` yet, so the first publish run plans the variant's first build.
- 2026-11-22: Local AI variant image is 3.46 GB against 2.47 GB for the custom image.
- 2026-11-22: In publish runs, `build-and-test.yml` skips the AI variant ("not wired yet") and uploads only custom candidates. Route 4 replaces this skip with real variant publishing.
- 2026-11-22: `build-and-test.yml` takes a `variant` input and is called once per image (`image.yml` and `publish.yml`), so an AI variant failure never fails the custom image's build job. The temporary matrix skip from route 3 is gone.
- 2026-11-22: The AI variant has no vulnerability scan job. The custom image's report-only scan is unchanged; adding one for the variant is optional.
- 2026-11-22: After the independent check, `commit_lock.py` exits non-zero when one image's part fails but still commits the other's verified part, so the failure issue opens without losing a publish.
- 2026-11-22: The existing repositories' Docker Hub tag immutability rule is `^[0-9]+\.[0-9]+\.[0-9]+-[0-9]{8}-[0-9]{4}$` (build tags only). `n8n-ytdlp-ai` was created with immutability off; the user sets the same rule in the Docker Hub UI.
- 2026-11-24: Correction: every `.work/` file is Markdown, which the publish workflow's `**.md` paths-ignore already skips, so record-only pushes to `main` never publish. The `.work/**` paths-ignore plan of 2026-11-22 was unnecessary and is dropped; the record goes to `main` with this branch.
