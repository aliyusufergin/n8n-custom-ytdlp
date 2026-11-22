"""Commit a verified published lock on current main using a normal push."""

import argparse
import json
from pathlib import Path
import re
import subprocess


def read_lock(path: Path) -> dict:
    """Return a lock file's contents; a missing lock file records no build inputs."""
    return json.loads(path.read_text()) if path.exists() else {}


# The lock keys each image owns: the custom image's build inputs and published state,
# and the AI variant's tools and published state. A key moves only with its image's publish.
CUSTOM_KEYS = ("n8n", "yt_dlp", "ffmpeg")
AI_VARIANT_KEYS = ("codex", "agy", "published_ai_variant")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--previous-lock", type=Path, required=True,
                        help="Lock on main that the plan compared against; a missing file means main had none")
    parser.add_argument("--result", type=Path, help="The custom image's verified published lock")
    parser.add_argument("--ai-result", type=Path, help="The AI variant's verified publishing result")
    args = parser.parse_args()
    if args.result is None and args.ai_result is None:
        parser.error("nothing was published")
    plan = json.loads(args.plan.read_text())
    previous = read_lock(args.previous_lock)
    lock_path = args.repository / "build-inputs.lock.json"
    current = read_lock(lock_path)
    parts = []
    updates = {}
    if args.result is not None:
        published = json.loads(args.result.read_text())
        if (published["published"]["build_tag"] != plan["build_tag"]
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", published["published"]["image_digest"])):
            raise ValueError("missing successful publishing result")
        for name in CUSTOM_KEYS:
            if current.get(name) != previous.get(name):
                raise ValueError("main's build inputs changed during this run; run the workflow again")
            if published[name] != plan["new_lock"][name]:
                raise ValueError("published inputs differ from the plan")
            updates[name] = published[name]
        updates["published"] = published["published"]
        # The plan's summary compares against the previous lock, which main still matches.
        parts.append(f'{plan["change_summary"]} ({plan["build_tag"]})')
    if args.ai_result is not None:
        ai_plan = plan["ai_variant"]
        result = json.loads(args.ai_result.read_text())
        state = result["published_ai_variant"]
        if (state["build_tag"] != ai_plan["build_tag"]
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", state["image_digest"])):
            raise ValueError("missing successful AI variant publishing result")
        if state["build_inputs"] != ai_plan["build_inputs"]:
            raise ValueError("published AI variant inputs differ from the plan")
        for name in AI_VARIANT_KEYS:
            if current.get(name) != previous.get(name):
                raise ValueError("main's AI variant state changed during this run; run the workflow again")
        updates.update(codex=state["build_inputs"]["codex"], agy=state["build_inputs"]["agy"],
                       published_ai_variant=state)
        parts.append(f'AI variant {ai_plan["change_summary"]} ({ai_plan["build_tag"]})')
    lock_path.write_text(json.dumps({**current, **updates}, indent=2) + "\n")
    message = "Publish " + "; ".join(parts)
    for command in (["git", "add", "--", "build-inputs.lock.json"],
                    ["git", "-c", "user.name=github-actions[bot]", "-c",
                     "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "commit", "-m", message],
                    ["git", "push", "origin", "HEAD:main"]):
        subprocess.run(command, cwd=args.repository, check=True)


if __name__ == "__main__":
    main()
