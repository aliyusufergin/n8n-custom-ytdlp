"""Build for the local Docker host from locked inputs, then test the image."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from publish import inspect_archive


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "build-inputs.lock.json")
    parser.add_argument("--image", default="n8n-ytdlp:local")
    parser.add_argument("--plan", type=Path, help="Use the publishing plan's lock and build tag")
    parser.add_argument("--archive", type=Path, help="Export an attested OCI archive (requires containerd Docker)")
    parser.add_argument("--youtube-network", choices=("bridge", "none"), default="bridge",
                        help="Use none to reproduce a warning-only YouTube network failure")
    parser.add_argument("tests", nargs="*", help="Optional unittest test names")
    args = parser.parse_args()
    if args.archive and not args.plan:
        parser.error("--archive requires --plan")
    plan = json.loads(args.plan.read_text()) if args.plan else None
    if plan:
        if plan["build"] is not True:
            parser.error("plan does not request a build")
        args.lock = args.plan.with_name("candidate.lock.json")
        args.lock.write_text(json.dumps(plan["new_lock"], indent=2) + "\n")
    lock = plan["new_lock"] if plan else json.loads(args.lock.read_text())
    host = subprocess.check_output(
        ["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"], text=True,
    ).strip()
    if host not in ("linux/amd64", "linux/arm64"):
        parser.error(f"Unsupported Docker host platform: {host}")
    now = datetime.now(timezone.utc)
    build_tag = plan["build_tag"] if plan else f'{lock["n8n"]["version"]}-{now:%Y%m%d-%H%M}'
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
    command = ["docker", "buildx", "build", "--platform", host, "--tag", args.image]
    if args.archive:
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        scanner = "docker/buildkit-syft-scanner@sha256:ae4f3b554449e7e25548e7d8ccc029d17357348e30c6e3df01b92bc93654d6a9"
        command.extend(["--provenance=mode=max", f"--attest=type=sbom,generator={scanner}", "--output",
                        f"type=oci,dest={args.archive},oci-mediatypes=true"])
    else:
        command.append("--load")
    for name, value in build_args.items():
        command.extend(["--build-arg", f"{name}={value}"])
    subprocess.run([*command, str(ROOT)], check=True)
    if args.archive:
        evidence = inspect_archive(args.archive, host.split("/")[1], build_tag)
        subprocess.run(["docker", "load", "--input", str(args.archive)], check=True)
        # Containerd's platform-specific ID is the OCI image manifest digest.
        loaded_digest = subprocess.check_output(
            ["docker", "image", "inspect", "--platform", host,
             "--format", "{{.Id}}", args.image], text=True,
        ).strip()
        if loaded_digest != evidence["image_digest"]:
            raise ValueError("loaded candidate differs from the OCI archive")
    subprocess.run(
        [sys.executable, str(ROOT / "tests/test_image.py"), args.image,
         str(args.lock.resolve()), "--youtube-network", args.youtube_network,
         "--build-tag", build_tag,
         *args.tests], check=True,
    )
    if args.archive:
        args.archive.with_suffix(".json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
