"""Build for the local Docker host from locked inputs, then test the image."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "build-inputs.lock.json")
    parser.add_argument("--image", default="n8n-ytdlp:local")
    parser.add_argument("tests", nargs="*", help="Optional unittest test names")
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    host = subprocess.check_output(
        ["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"], text=True,
    ).strip()
    if host not in ("linux/amd64", "linux/arm64"):
        parser.error(f"Unsupported Docker host platform: {host}")
    now = datetime.now(timezone.utc)
    build_tag = f'{lock["n8n"]["version"]}-{now:%Y%m%d-%H%M}'
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    build_args = {
        "N8N_IMAGE": f'n8nio/n8n@{lock["n8n"]["image_digest"]}',
        "FFMPEG_IMAGE": f'mwader/static-ffmpeg@{lock["ffmpeg"]["image_digest"]}',
        "N8N_VERSION": lock["n8n"]["version"],
        "N8N_DIGEST": lock["n8n"]["image_digest"],
        "RUNNERS_DIGEST": lock["n8n"]["runners_digest"],
        "YT_DLP_TAG": lock["yt_dlp"]["tag"],
        "YT_DLP_SHA256_AMD64": lock["yt_dlp"]["sha256"]["yt-dlp_musllinux"],
        "YT_DLP_SHA256_ARM64": lock["yt_dlp"]["sha256"]["yt-dlp_musllinux_aarch64"],
        "FFMPEG_VERSION": lock["ffmpeg"]["version"],
        "FFMPEG_DIGEST": lock["ffmpeg"]["image_digest"],
        "BUILD_TAG": build_tag,
        "REVISION": revision,
        "CREATED": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    # BuildKit's cache alone does not make the upstream available to image inspect.
    subprocess.run(["docker", "pull", "--platform", host, build_args["N8N_IMAGE"]], check=True)
    command = ["docker", "buildx", "build", "--load", "--platform", host, "--tag", args.image]
    for name, value in build_args.items():
        command.extend(["--build-arg", f"{name}={value}"])
    subprocess.run([*command, str(ROOT)], check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "tests/test_image.py"), args.image,
         str(args.lock.resolve()), *args.tests], check=True,
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
