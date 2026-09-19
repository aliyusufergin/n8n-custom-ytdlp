# Recorded upstream responses

Each directory is one recording for `scripts/updater.py --replay`. A response
file is named by its URL, percent-encoded with `urllib.parse.quote(url, safe="")`.
Response bodies are stored byte for byte as upstream served them.

- `yt-dlp-nightly-2026.09.16.232951`: the latest yt-dlp nightly on 2026-09-19,
  recorded with `--record`.
- `yt-dlp-nightly-2025.08.30.232839`: the last nightly published without
  musllinux assets. Its `releases/tags/2025.08.30.232839` response is stored
  under the `releases/latest` URL; its checksum list and signature are unchanged
  and validly signed.

Record a new snapshot from live upstream with:

```sh
python3 scripts/updater.py --trigger scheduled --record tests/fixtures/upstream/<name>
```
