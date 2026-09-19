"""Resolve upstream build inputs and print the updater's plan."""

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
YT_DLP_NIGHTLY = "yt-dlp/yt-dlp-nightly-builds"
YT_DLP_ASSETS = ("yt-dlp_musllinux", "yt-dlp_musllinux_aarch64")
# yt-dlp's public.key, committed so that no key is ever fetched at run time.
YT_DLP_KEY = Path(__file__).with_name("yt-dlp-signing-key.asc")
YT_DLP_FINGERPRINT = "AC0CBBE6848D6A873464AF4E57CF65933B5A7581"
# Each build input's lock key, display name and identifying field.
BUILD_INPUTS = (("n8n", "n8n", "version"), ("yt_dlp", "yt-dlp", "tag"), ("ffmpeg", "ffmpeg", "version"))


class UpstreamError(Exception):
    """Upstream cannot provide trustworthy build inputs, so the run must fail."""


class Upstream:
    """Upstream responses, fetched live or replayed from a recording directory.

    A recording holds one file per URL, named by the URL percent-encoded with
    urllib.parse.quote(url, safe=""). Replay never falls back to the network.
    """

    def __init__(self, replay: Path | None = None, record: Path | None = None) -> None:
        self.replay = replay
        self.record = record

    def get(self, url: str) -> bytes:
        name = quote(url, safe="")
        if self.replay is not None:
            try:
                return (self.replay / name).read_bytes()
            except FileNotFoundError:
                raise UpstreamError(f"no recorded response for {url}") from None
        request = Request(url)
        if url.startswith("https://api.github.com/"):
            request.add_header("Accept", "application/vnd.github+json")
            if token := os.environ.get("GITHUB_TOKEN"):
                # Unredirected headers never follow a redirect to another host.
                request.add_unredirected_header("Authorization", f"Bearer {token}")
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read()
        except OSError as error:
            raise UpstreamError(f"cannot fetch {url}: {error}") from error
        if self.record is not None:
            self.record.mkdir(parents=True, exist_ok=True)
            (self.record / name).write_bytes(body)
        return body


def verify_yt_dlp_signature(sums: bytes, signature: bytes) -> None:
    """Accept only a single good signature by the pinned yt-dlp key."""
    # gpgv reads binary keyrings only, so strip the ASCII armor and its CRC line.
    armor = YT_DLP_KEY.read_text().splitlines()
    body = armor[armor.index("") + 1:armor.index("-----END PGP PUBLIC KEY BLOCK-----")]
    keyring = base64.b64decode("".join(line for line in body if not line.startswith("=")))
    with tempfile.TemporaryDirectory() as home:
        files = {"keyring.gpg": keyring, "SHA2-256SUMS.sig": signature, "SHA2-256SUMS": sums}
        for name, data in files.items():
            Path(home, name).write_bytes(data)
        try:
            result = subprocess.run(
                ["gpgv", "--homedir", home, "--status-fd", "1",
                 "--keyring", str(Path(home, "keyring.gpg")),
                 str(Path(home, "SHA2-256SUMS.sig")), str(Path(home, "SHA2-256SUMS"))],
                capture_output=True, text=True, errors="replace",
            )
        except FileNotFoundError:
            raise UpstreamError("gpgv is required to verify yt-dlp's SHA2-256SUMS signature") from None
    status = [line.split()[1:] for line in result.stdout.splitlines() if line.startswith("[GNUPG:] ")]
    keywords = [fields[0] for fields in status]
    # VALIDSIG ends with the fingerprint of the signing key's primary key.
    signers = [fields[-1] for fields in status if fields[0] == "VALIDSIG"]
    if (result.returncode != 0 or keywords.count("NEWSIG") != 1 or "GOODSIG" not in keywords
            or signers != [YT_DLP_FINGERPRINT]):
        raise UpstreamError(f"yt-dlp SHA2-256SUMS signature is not a good signature by "
                            f"{YT_DLP_FINGERPRINT}: {result.stderr.strip()}")


def resolve_yt_dlp(upstream: Upstream) -> dict:
    """Return the lock entry for the yt-dlp nightly that releases/latest names."""
    release = json.loads(upstream.get(f"https://api.github.com/repos/{YT_DLP_NIGHTLY}/releases/latest"))
    tag = release["tag_name"]
    # The tag becomes part of download URLs and image labels.
    if not isinstance(tag, str) or not re.fullmatch(r"[0-9]+(\.[0-9]+)+", tag):
        raise UpstreamError(f"unexpected yt-dlp nightly tag: {tag!r}")
    assets = {asset["name"] for asset in release["assets"]}
    for name in ("SHA2-256SUMS", "SHA2-256SUMS.sig", *YT_DLP_ASSETS):
        if name not in assets:
            raise UpstreamError(f"yt-dlp nightly {tag} has no {name} asset")
    download = f"https://github.com/{YT_DLP_NIGHTLY}/releases/download/{tag}/"
    sums = upstream.get(download + "SHA2-256SUMS")
    verify_yt_dlp_signature(sums, upstream.get(download + "SHA2-256SUMS.sig"))
    checksums = {name: checksum for checksum, name
                 in re.findall(r"^([0-9a-f]{64})  (\S+)$", sums.decode(), re.MULTILINE)}
    for name in YT_DLP_ASSETS:
        if name not in checksums:
            raise UpstreamError(f"yt-dlp nightly {tag} SHA2-256SUMS has no checksum for {name}")
    return {"tag": tag, "sha256": {name: checksums[name] for name in YT_DLP_ASSETS}}


def describe_changes(lock: dict, new_lock: dict) -> list[str]:
    """Name each changed build input, e.g. "n8n 2.38.7 → 2.38.8"."""
    changes = []
    for key, name, field in BUILD_INPUTS:
        before, after = lock[key], new_lock[key]
        if before[field] != after[field]:
            changes.append(f"{name} {before[field]} → {after[field]}")
        elif before != after:
            changes.append(f"{name} {after[field]} new digest")
    return changes


def run_time(value: str) -> datetime:
    try:
        now = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if now.tzinfo is None:
            raise ValueError("timezone is required")
        return now.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise argparse.ArgumentTypeError(f"invalid run time: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "build-inputs.lock.json")
    parser.add_argument("--trigger", required=True,
                        choices=("scheduled", "manual", "push", "pull_request"))
    parser.add_argument("--now", type=run_time,
                        help="Run time as ISO 8601 with a timezone (default: current UTC)")
    upstream = parser.add_mutually_exclusive_group()
    upstream.add_argument("--replay", type=Path,
                          help="Answer upstream requests only from responses recorded in this directory")
    upstream.add_argument("--record", type=Path,
                          help="Also save every live upstream response in this directory for --replay")
    args = parser.parse_args()
    try:
        lock = json.loads(args.lock.read_text())
    except (OSError, ValueError) as error:
        parser.error(f"cannot read lock file: {error}")
    try:
        version = lock["n8n"]["version"]
    except (KeyError, TypeError):
        parser.error("lock file must contain an n8n version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        parser.error("n8n version must be numeric X.Y.Z")
    if version.split(".")[0] != "2":
        parser.error("n8n version must remain on the major 2 stable track")
    now = args.now if args.now is not None else datetime.now(timezone.utc)
    try:
        new_lock = {**lock, "yt_dlp": resolve_yt_dlp(Upstream(args.replay, args.record))}
    except UpstreamError as error:
        parser.exit(1, f"{parser.prog}: error: {error}\n")
    major, minor, _ = version.split(".")
    changes = describe_changes(lock, new_lock)
    if changes:
        build, reason, summary = True, "build inputs changed", ", ".join(changes)
    elif args.trigger in ("manual", "push", "pull_request"):
        build, reason, summary = True, f"{args.trigger} trigger", f"n8n {version} rebuild"
    else:
        build, reason, summary = False, "build inputs unchanged", None
    print(json.dumps({
        "build": build,
        "reason": reason,
        "change_summary": summary,
        "new_lock": new_lock,
        "floating_tags": [major, f"{major}.{minor}", version],
        "build_tag": f"{version}-{now.year:04d}{now.month:02d}{now.day:02d}-{now:%H%M}",
        "notices": [],
    }))


if __name__ == "__main__":
    main()
