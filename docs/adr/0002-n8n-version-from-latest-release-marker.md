# The n8n version comes from GitHub's "latest release" marker, not the highest version

The custom image follows n8n's stable track by reading `releases/latest` of `n8n-io/n8n` and accepting only `n8n@2.*`. It rebuilds when that version or the upstream image digest changes. The obvious rule, "highest non-prerelease 2.x release", is wrong for n8n for two reasons. New minors ship as beta while older minors keep receiving patches. GitHub prerelease flags are also inconsistent: `n8n@2.38.1` was a beta-line patch but is not marked prerelease. That rule would therefore publish beta builds as stable to every auto-updating deployment. Evidence: `docs/research/n8n-2x-docker-image.md` §1.

## Consequences

- Once n8n 3.x becomes the "latest release", the major-2 filter rejects it. The updater then follows n8n's 2.x maintenance releases while they exist, otherwise freezes on the last 2.x. Either way it opens an issue.
- Upstream digests are tracked as well as version strings, because n8n has re-pushed an existing version tag with new content (2.38.0).
