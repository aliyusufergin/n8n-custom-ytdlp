"""Print an updater plan from locked build inputs without resolving upstreams."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


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
    major, minor, _ = version.split(".")
    build = args.trigger in ("manual", "push", "pull_request")
    print(json.dumps({
        "build": build,
        "reason": f"{args.trigger} trigger" if build else "build inputs unchanged",
        "new_lock": lock,
        "floating_tags": [major, f"{major}.{minor}", version],
        "build_tag": f"{version}-{now.year:04d}{now.month:02d}{now.day:02d}-{now:%H%M}",
        "notices": [],
    }))


if __name__ == "__main__":
    main()
