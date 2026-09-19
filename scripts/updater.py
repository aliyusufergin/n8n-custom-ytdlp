"""Resolve upstream build inputs and print the updater's plan."""

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
N8N_REPO = "n8n-io/n8n"
# The custom image follows n8n's stable track only while its major version is this one.
STABLE_MAJOR = "2"
VERSION = r"[0-9]+\.[0-9]+\.[0-9]+"
# Each n8n lock field and the Docker Hub repository whose index digest it records.
N8N_IMAGES = (("image_digest", "n8nio/n8n"), ("runners_digest", "n8nio/runners"))
DOCKER_HUB = "https://registry-1.docker.io/v2"
IMAGE_INDEX = ("application/vnd.oci.image.index.v1+json, "
               "application/vnd.docker.distribution.manifest.list.v2+json")
YT_DLP_NIGHTLY_REPO = "yt-dlp/yt-dlp-nightly-builds"
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
    urllib.parse.quote(url, safe=""); a HEAD response's file is named the same way
    after "HEAD " + url. Replay never falls back to the network.
    """

    def __init__(self, replay: Path | None = None, record: Path | None = None) -> None:
        self.replay = replay
        self.record = record

    @staticmethod
    def replayed(recording: Path, name: str, label: str) -> bytes:
        try:
            return (recording / name).read_bytes()
        except FileNotFoundError:
            raise UpstreamError(f"no recorded response for {label}") from None

    def save(self, name: str, body: bytes) -> None:
        if self.record is not None:
            self.record.mkdir(parents=True, exist_ok=True)
            (self.record / name).write_bytes(body)

    def get(self, url: str) -> bytes:
        name = quote(url, safe="")
        if self.replay is not None:
            return self.replayed(self.replay, name, url)
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
        self.save(name, body)
        return body

    def head_manifest(self, url: str) -> dict[str, str] | None:
        """Return a registry manifest HEAD response's recorded headers, or None if url does not exist.

        The response is recorded as JSON: {"status": 200 or 404, "headers": {...}}.
        """
        name = quote(f"HEAD {url}", safe="")
        if self.replay is not None:
            response = json.loads(self.replayed(self.replay, name, f"HEAD {url}"))
        else:
            response = self.head_manifest_live(url)
            self.save(name, json.dumps(response, indent=2).encode() + b"\n")
        return response["headers"] if response["status"] == 200 else None

    @staticmethod
    def head_manifest_live(url: str) -> dict:
        request = Request(url, method="HEAD", headers={"Accept": IMAGE_INDEX})
        try:
            while True:
                try:
                    with urlopen(request, timeout=60) as response:
                        # Only the digest is recorded; Docker Hub's other headers name the requesting IP.
                        digest = response.headers["Docker-Content-Digest"]
                        return {"status": 200, "headers": {"docker-content-digest": digest}}
                except HTTPError as error:
                    if error.code == 404:
                        return {"status": 404, "headers": {}}
                    # Docker Hub asks even anonymous clients for a bearer token per repository.
                    challenge = error.headers.get("WWW-Authenticate", "")
                    if (error.code != 401 or not challenge.startswith("Bearer ")
                            or request.has_header("Authorization")):
                        raise
                parameters = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
                realm = parameters.pop("realm")
                with urlopen(f"{realm}?{urlencode(parameters)}", timeout=60) as token:
                    request.add_unredirected_header("Authorization", f"Bearer {json.load(token)['token']}")
        except (OSError, KeyError, ValueError) as error:
            raise UpstreamError(f"cannot fetch HEAD {url}: {error}") from error


def index_digest(upstream: Upstream, repository: str, tag: str) -> str | None:
    """Return a Docker Hub tag's image index digest, or None while the tag does not exist."""
    # Manifest HEAD requests do not count against Docker Hub's pull limit.
    headers = upstream.head_manifest(f"{DOCKER_HUB}/{repository}/manifests/{tag}")
    if headers is None:
        return None
    digest = headers.get("docker-content-digest")
    # The digest becomes a build argument and an image label.
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise UpstreamError(f"{repository}:{tag} has an unexpected index digest: {digest!r}")
    return digest


def n8n_version(upstream: Upstream, locked: str) -> tuple[str, list[dict]]:
    """Return the stable-track n8n version to build (ADR 0002) and any notices to raise."""
    release = json.loads(upstream.get(f"https://api.github.com/repos/{N8N_REPO}/releases/latest"))
    # Only the latest-release marker counts; n8n's prerelease flags are unreliable.
    tag = release["tag_name"]
    match = re.fullmatch(rf"n8n@({VERSION})", tag) if isinstance(tag, str) else None
    if match is None:
        raise UpstreamError(f"unexpected n8n latest release tag: {tag!r}")
    marker = match[1]
    major = marker.split(".")[0]
    if major == STABLE_MAJOR:
        return marker, []
    # Follow patches of the locked 2.x minor. n8n creates each n8n@X.Y.Z tag with its release,
    # and one request lists a minor's tags where the releases list needs many pages; a tag
    # whose images were never pushed is skipped like any version that is not pushed yet.
    minor, patch = locked.rsplit(".", 1)
    refs = json.loads(upstream.get(
        f"https://api.github.com/repos/{N8N_REPO}/git/matching-refs/tags/n8n@{minor}."))
    patches = [int(found[1]) for ref in refs
               if (found := re.fullmatch(rf"refs/tags/n8n@{re.escape(minor)}\.([0-9]+)", ref["ref"]))]
    notice = {
        "key": f"n8n-{major}",
        "title": f"n8n {major}.x available",
        "body": f"n8n's latest release is now n8n {marker}. The custom image never moves to a new "
                f"major version by itself: it keeps following patches of n8n {minor}, its current "
                f"2.x minor, and stays on the last one when they stop. Moving to {major}.x is the "
                f"maintainer's decision (ADR 0002).",
    }
    return f"{minor}.{max([int(patch), *patches])}", [notice]


def resolve_n8n(upstream: Upstream, locked: dict) -> tuple[dict, list[dict]]:
    """Return the n8n lock entry with both upstream index digests, and any notices to raise."""
    version, notices = n8n_version(upstream, locked["version"])
    entry = {"version": version}
    for field, repository in N8N_IMAGES:
        if (digest := index_digest(upstream, repository, version)) is None:
            if version == locked["version"]:
                raise UpstreamError(f"{repository}:{version} of the locked n8n version no longer exists")
            # n8n usually pushes its images before it marks the release; a later run retries.
            print(f"{repository}:{version} is not pushed yet; keeping n8n {locked['version']}",
                  file=sys.stderr)
            return locked, notices
        entry[field] = digest
    return entry, notices


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
    release = json.loads(upstream.get(f"https://api.github.com/repos/{YT_DLP_NIGHTLY_REPO}/releases/latest"))
    tag = release["tag_name"]
    # The tag becomes part of download URLs and image labels.
    if not isinstance(tag, str) or not re.fullmatch(r"[0-9]+(\.[0-9]+)+", tag):
        raise UpstreamError(f"unexpected yt-dlp nightly tag: {tag!r}")
    assets = {asset["name"] for asset in release["assets"]}
    for name in ("SHA2-256SUMS", "SHA2-256SUMS.sig", *YT_DLP_ASSETS):
        if name not in assets:
            raise UpstreamError(f"yt-dlp nightly {tag} has no {name} asset")
    download = f"https://github.com/{YT_DLP_NIGHTLY_REPO}/releases/download/{tag}/"
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
            changes.append(f"{name} {after[field]} republished")
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
    recording = parser.add_mutually_exclusive_group()
    recording.add_argument("--replay", type=Path,
                          help="Answer upstream requests only from responses recorded in this directory")
    recording.add_argument("--record", type=Path,
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
    if not isinstance(version, str) or not re.fullmatch(VERSION, version):
        parser.error("n8n version must be numeric X.Y.Z")
    if version.split(".")[0] != STABLE_MAJOR:
        parser.error("n8n version must remain on the major 2 stable track")
    now = args.now if args.now is not None else datetime.now(timezone.utc)
    upstream = Upstream(args.replay, args.record)
    try:
        n8n, notices = resolve_n8n(upstream, lock["n8n"])
        new_lock = {**lock, "n8n": n8n, "yt_dlp": resolve_yt_dlp(upstream)}
    except UpstreamError as error:
        parser.exit(1, f"{parser.prog}: error: {error}\n")
    version = n8n["version"]
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
        # Each notice is {"key", "title", "body"}; scripts/notify.py opens at most one issue per key.
        "notices": notices,
    }))


if __name__ == "__main__":
    main()
