# Recorded upstream responses

Each directory is one recording of one upstream. The tests copy one n8n and one
yt-dlp recording into a single directory for `scripts/updater.py --replay`. A
response file is named by its URL, percent-encoded with
`urllib.parse.quote(url, safe="")`. Response bodies are stored byte for byte as
upstream served them.

A registry HEAD response has no body. Its file is named by `"HEAD " + url`,
percent-encoded the same way, and holds `{"status": 200, "headers":
{"docker-content-digest": "sha256:..."}}`, or `{"status": 404, "headers": {}}`
for a tag that does not exist. No other header is recorded, because Docker Hub's
headers name the requesting IP.

- `n8n-2.39.8`: the stable-track release that `releases/latest` named on
  2026-09-19, with the `n8nio/n8n` and `n8nio/runners` digests of `2.39.8`,
  recorded with `--record`.
- `n8n-2.38.7`: the release `n8n@2.38.7`, whose `releases/tags/n8n@2.38.7`
  response is stored under the `releases/latest` URL, with the digests of
  `2.38.7` and the tags of the `2.38` minor (`2.38.0` to `2.38.7`), all recorded
  on 2026-09-19.
- `n8n-2.37.11`: the release that `releases/latest` named on 2026-09-07, while
  beta-line `n8n@2.38.1` was not flagged prerelease. Its
  `releases/tags/n8n@2.37.11` response is stored under the `releases/latest`
  URL, with the digests of `2.37.11` recorded on 2026-09-19.
- `yt-dlp-nightly-2026.09.16.232951`: the yt-dlp nightly that `releases/latest`
  named on 2026-09-19, recorded with `--record`.
- `yt-dlp-nightly-2025.08.30.232839`: the last nightly published without
  musllinux assets. Its `releases/tags/2025.08.30.232839` response is stored
  under the `releases/latest` URL; its checksum list and signature are unchanged
  and validly signed.

Record a new snapshot from live upstream, then split its files into one
directory per upstream:

```sh
python3 scripts/updater.py --trigger scheduled --record <snapshot>
```
