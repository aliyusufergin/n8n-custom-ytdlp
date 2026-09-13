"""Commit a verified published lock on current main using a normal push."""

import argparse
import json
from pathlib import Path
import re
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--previous-lock", type=Path, required=True,
                        help="Lock from the source revision that was built")
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    published = json.loads(args.result.read_text())
    previous = json.loads(args.previous_lock.read_text())
    if (published["published"]["build_tag"] != plan["build_tag"]
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", published["published"]["image_digest"])):
        raise ValueError("missing successful publishing result")
    lock_path = args.repository / "build-inputs.lock.json"
    current = json.loads(lock_path.read_text())
    for name in ("n8n", "yt_dlp", "ffmpeg"):
        if current[name] != previous[name]:
            raise ValueError("main's build inputs changed during this run; run the workflow again")
        if published[name] != plan["new_lock"][name]:
            raise ValueError("published inputs differ from the plan")
    changes = []
    for name, field in (("n8n", "version"), ("yt_dlp", "tag"), ("ffmpeg", "version")):
        before, after = current[name][field], published[name][field]
        if before != after:
            changes.append(f"{name} {before} -> {after}")
        elif current[name] != published[name]:
            changes.append(f"{name} build inputs")
    if not changes:
        changes.append(f'n8n {published["n8n"]["version"]} rebuild')
    message = f'Publish {", ".join(changes)} ({plan["build_tag"]})'
    lock_path.write_text(json.dumps(published, indent=2) + "\n")
    for command in (["git", "add", "--", "build-inputs.lock.json"],
                    ["git", "-c", "user.name=github-actions[bot]", "-c",
                     "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "commit", "-m", message],
                    ["git", "push", "origin", "HEAD:main"]):
        subprocess.run(command, cwd=args.repository, check=True)


if __name__ == "__main__":
    main()
