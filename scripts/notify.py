"""Report a publishing run's outcome and its plan's notices as GitHub Issues.

The publishing workflow runs this with GH_TOKEN and GH_REPO set; every call goes
to the GitHub REST API through the gh CLI.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess


FAILURE_LABEL = "updater-failure"
NOTICE_LABEL = "updater-notice"
# These labels belong to the updater, not to triage: (color, description).
LABELS = {
    FAILURE_LABEL: ("B60205", "A publishing run failed; the next successful run closes this"),
    NOTICE_LABEL: ("1D76DB", "A one-off notice raised by the updater's plan"),
}
ISSUES = "repos/{owner}/{repo}/issues"
# A notice issue's body carries its key, so a closed notice is never raised again.
NOTICE_MARKER = "<!-- updater-notice: {} -->"


def gh(*args: str) -> str:
    # gh reports its own errors on stderr, which stays in the job log.
    return subprocess.check_output(["gh", *args], text=True)


def labelled_issues(label: str, state: str) -> list[dict]:
    """Return the number and body of every issue with the label, oldest first."""
    output = gh("api", "--paginate",
                f"{ISSUES}?labels={label}&state={state}&direction=asc&per_page=100",
                "--jq", ".[] | select(.pull_request | not) | {number, body}")
    return [json.loads(line) for line in output.splitlines()]


def create_labelled_issue(label: str, title: str, body: str) -> int:
    """Create the label if it is missing, then an issue with it."""
    color, description = LABELS[label]
    gh("label", "create", label, "--color", color, "--description", description, "--force")
    issue = json.loads(gh("api", ISSUES, "-f", f"title={title}", "-f", f"body={body}",
                          "-f", f"labels[]={label}"))
    return issue["number"]


def comment(number: int, body: str) -> None:
    gh("api", f"{ISSUES}/{number}/comments", "-f", f"body={body}", "--silent")


def report_failure(run_url: str, failed_jobs: list[str]) -> None:
    jobs = ", ".join(f"`{name}`" for name in failed_jobs)
    if issues := labelled_issues(FAILURE_LABEL, "open"):
        number = issues[0]["number"]
        comment(number, f"Publishing run {run_url} failed again (failed jobs: {jobs}).")
        print(f"Commented on failure issue #{number}")
        return
    number = create_labelled_issue(FAILURE_LABEL, "Publishing workflow failed",
                                   f"Publishing run {run_url} failed (failed jobs: {jobs}).\n\n"
                                   "Each later failed run comments here with its run link. "
                                   "The next successful run closes this issue.")
    print(f"Opened failure issue #{number}")


def report_success(run_url: str) -> None:
    for issue in labelled_issues(FAILURE_LABEL, "open"):
        number = issue["number"]
        comment(number, f"Publishing run {run_url} succeeded, so this failure is resolved.")
        gh("api", "-X", "PATCH", f"{ISSUES}/{number}",
           "-f", "state=closed", "-f", "state_reason=completed", "--silent")
        print(f"Closed failure issue #{number}")


def raise_notices(notices: list[dict], run_url: str) -> None:
    """Open one issue per notice key, unless any issue, even a closed one, has that key."""
    for notice in notices:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", notice["key"]):
            raise ValueError(f'invalid notice key: {notice["key"]!r}')
    if not notices:
        return
    bodies = [issue["body"] or "" for issue in labelled_issues(NOTICE_LABEL, "all")]
    for notice in notices:
        marker = NOTICE_MARKER.format(notice["key"])
        if any(marker in body for body in bodies):
            print(f'Notice {notice["key"]} was already raised')
            continue
        body = f'{notice["body"]}\n\nRaised by publishing run {run_url}.\n\n{marker}'
        number = create_labelled_issue(NOTICE_LABEL, notice["title"], body)
        bodies.append(body)
        print(f'Opened notice issue #{number} for {notice["key"]}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--needs", type=json.loads, required=True,
                        help="The notifying job's toJSON(needs): every other job's result")
    parser.add_argument("--plan", type=Path, help="This run's plan, if planning succeeded")
    args = parser.parse_args()
    results = {name: job["result"] for name, job in args.needs.items()}
    # Skipped jobs are the plan's decision not to build; a cancelled job, e.g. a timeout, failed.
    if failed_jobs := sorted(name for name, result in results.items()
                             if result not in ("success", "skipped")):
        report_failure(args.run_url, failed_jobs)
    elif "success" in results.values():
        report_success(args.run_url)
    if args.plan is not None:
        raise_notices(json.loads(args.plan.read_text())["notices"], args.run_url)


if __name__ == "__main__":
    main()
