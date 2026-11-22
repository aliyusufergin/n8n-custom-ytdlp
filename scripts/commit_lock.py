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
    parts, updates, errors = [], {}, []
    # Each image is checked and recorded on its own, so one image's problem never drops
    # the other's verified publish. A part already on main, as after "Re-run failed jobs",
    # is skipped.
    if args.result is not None:
        try:
            part = custom_part(plan, previous, current, json.loads(args.result.read_text()))
            if part is not None:
                updates.update(part)
                # The plan's summary compares against the previous lock, which main still matches.
                parts.append(f'{plan["change_summary"]} ({plan["build_tag"]})')
        except ValueError as error:
            errors.append(f"custom image: {error}")
    if args.ai_result is not None:
        try:
            part = ai_part(plan, previous, current, json.loads(args.ai_result.read_text()))
            if part is not None:
                updates.update(part)
                ai_plan = plan["ai_variant"]
                parts.append(f'AI variant {ai_plan["change_summary"]} ({ai_plan["build_tag"]})')
        except ValueError as error:
            errors.append(f"AI variant: {error}")
    if parts:
        lock_path.write_text(json.dumps({**current, **updates}, indent=2) + "\n")
        message = "Publish " + "; ".join(parts)
        for command in (["git", "add", "--", "build-inputs.lock.json"],
                        ["git", "-c", "user.name=github-actions[bot]", "-c",
                         "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                         "commit", "-m", message],
                        ["git", "push", "origin", "HEAD:main"]):
            subprocess.run(command, cwd=args.repository, check=True)
    if errors:
        raise SystemExit("; ".join(errors))


def custom_part(plan: dict, previous: dict, current: dict, published: dict) -> dict | None:
    """Return the custom image's lock keys to write, or None when main already has them."""
    if (published["published"]["build_tag"] != plan["build_tag"]
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", published["published"]["image_digest"])):
        raise ValueError("missing successful publishing result")
    for name in CUSTOM_KEYS:
        if published[name] != plan["new_lock"][name]:
            raise ValueError("published inputs differ from the plan")
    part = {name: published[name] for name in CUSTOM_KEYS}
    part["published"] = published["published"]
    if all(current.get(name) == value for name, value in part.items()):
        return None
    for name in (*CUSTOM_KEYS, "published"):
        if current.get(name) != previous.get(name):
            raise ValueError("main's build inputs changed during this run; run the workflow again")
    return part


def ai_part(plan: dict, previous: dict, current: dict, result: dict) -> dict | None:
    """Return the AI variant's lock keys to write, or None when main already has them."""
    ai_plan = plan["ai_variant"]
    state = result["published_ai_variant"]
    if (state["build_tag"] != ai_plan["build_tag"]
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", state["image_digest"])):
        raise ValueError("missing successful AI variant publishing result")
    if state["build_inputs"] != ai_plan["build_inputs"]:
        raise ValueError("published AI variant inputs differ from the plan")
    part = {"codex": state["build_inputs"]["codex"], "agy": state["build_inputs"]["agy"],
            "published_ai_variant": state}
    if all(current.get(name) == value for name, value in part.items()):
        return None
    for name in AI_VARIANT_KEYS:
        if current.get(name) != previous.get(name):
            raise ValueError("main's AI variant state changed during this run; run the workflow again")
    return part


if __name__ == "__main__":
    main()
