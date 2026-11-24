# Knowledge

- Checking here: the auto-mode classifier allows running upstream binaries in a throwaway container for `--version`/`--help`/offline runs, but refused a run that passed `--sandbox danger-full-access` (2026-11-22). Runs that sign in or spend the user's subscription are the user's to do.
- This machine has no arm64 emulation; arm64 is verified on CI's arm64 runners.
- On this dev machine, containers on Docker's default bridge network get ECONNRESET from Google hosts (google.com, oauth2.googleapis.com) while the host and `--network host` reach them; OpenAI and GitHub work either way. Use `--network host` for local checks that talk to Google. This is the machine, not the image.
- `.work/` holds only Markdown, which publish pushes ignore (`**.md`), so record-only pushes to `main` never publish.
- Local `main` lags behind GitHub: the publish workflow pushes lock commits there every few hours. Run `git fetch` and look at `origin/main` before reading the lock file or branching.
- The user writes in Turkish and has limited CI/CD background: explain choices in plain language with a concrete flow.
