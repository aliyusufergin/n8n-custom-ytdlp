# A scheduled lock-file updater, not Renovate, detects upstream changes

A single scheduled GitHub Actions workflow resolves the build inputs:

- the n8n stable-track version and digest
- the yt-dlp nightly tag and checksum
- the ffmpeg version and digest

When these differ from the committed lock file, the workflow builds, tests and publishes the custom image, and only then commits the new lock file. Git history is therefore the list of published images, and any image can be rebuilt from its commit. No third-party app holds write access to the repository.

## Considered Options

- **Renovate (Mend-hosted app).** Mature and free, but it needs a GitHub App with write access and custom regex and versioning rules for yt-dlp nightly tags. It opens frequent PRs and splits the system into a bot plus a publish workflow.
- **Dependabot.** Cannot follow an `ARG`-based `FROM` or GitHub release binaries such as yt-dlp nightly.
- **Resolve at build time without commits.** Least code, but build inputs are not recorded in git. The quiet repository also risks GitHub's 60-day auto-disable of scheduled workflows in public repos.

## Consequences

- The workflow commits to `main` with `GITHUB_TOKEN`. Such pushes do not trigger other workflows, so build, test and publish run in the same workflow run.
- Whether GitHub counts bot commits as activity for the 60-day rule is undocumented. The workflow also re-marks itself enabled through the API once a month.
