#!/usr/bin/env python3
"""Post open high and critical Dependabot alerts to a Slack workflow webhook.

Each alert is matched to its open Dependabot PR and reported with what stops
it from being fixed: no PR, failing CI, a merge conflict or a major bump. The
script posts when an alert needs a person or is critical, and posts a health
line on Mondays and on manual runs, so a silent channel means the check broke.

The repository is public and so are its Actions logs: only counts are printed.
"""

from __future__ import annotations

import datetime
import json
import os
import posixpath
import re
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com"
DEPENDABOT = "dependabot[bot]"
TITLE = re.compile(r"[Bb]ump (\S+) from (\S+) to (\S+?)(?: in (/\S*))?$")
FAILED_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}


@dataclass
class Finding:
    severity: str
    package: str
    manifest: str
    days_open: int
    url: str
    status: str
    needs_person: bool


def github(path: str, token: str) -> list | dict:
    url = path if path.startswith("https://") else f"{API}{path}"
    items: list = []
    while url:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
            links = response.headers.get("Link", "")
        if not isinstance(body, list):
            return body
        items.extend(body)
        url = next((part.split(";")[0].strip(" <>") for part in links.split(",") if 'rel="next"' in part), "")
    return items


def major_bump(old: str, new: str) -> bool:
    old_major, new_major = (re.match(r"v?(\d+)", version) for version in (old, new))
    return bool(old_major and new_major and old_major.group(1) != new_major.group(1))


def pr_for(alert: dict, prs: list[dict]) -> tuple[dict, re.Match] | None:
    package = alert["dependency"]["package"]["name"].lower()
    directory = "/" + posixpath.dirname(alert["dependency"]["manifest_path"])
    for pr in prs:
        match = TITLE.search(pr["title"])
        if (
            match
            and match.group(1).lower() == package
            and posixpath.normpath(match.group(4) or "/") == posixpath.normpath(directory)
        ):
            return pr, match
    return None


def pr_status(pr: dict, match: re.Match, check_runs: list[dict], mergeable_state: str) -> tuple[str, bool]:
    number = pr["number"]
    if any(run.get("conclusion") in FAILED_CONCLUSIONS for run in check_runs):
        return f"PR #{number}: CI failing", True
    if mergeable_state == "dirty":
        return f"PR #{number}: merge conflict", True
    if major_bump(match.group(2), match.group(3)):
        return f"PR #{number}: major version bump, needs a manual merge", True
    return f"PR #{number} open, no blocker found", False


def finding(alert: dict, status: str, needs_person: bool, now: datetime.datetime) -> Finding:
    created = datetime.datetime.fromisoformat(alert["created_at"].replace("Z", "+00:00"))
    return Finding(
        severity=alert["security_advisory"]["severity"],
        package=alert["dependency"]["package"]["name"],
        manifest=alert["dependency"]["manifest_path"],
        days_open=(now - created).days,
        url=alert["html_url"],
        status=status,
        needs_person=needs_person,
    )


def message(findings: list[Finding], heartbeat: bool) -> str | None:
    action = [f for f in findings if f.needs_person]
    critical = [f for f in findings if f.severity == "critical"]
    if not action and not critical:
        return (
            f"Dependabot check ran: no high or critical alert needs a person ({len(findings)} open)."
            if heartbeat
            else None
        )
    lines = [f"Dependabot: {len(action)} of {len(findings)} open high or critical alerts need a person."]
    for f in sorted(findings, key=lambda f: (not f.needs_person, f.severity != "critical", -f.days_open)):
        lines.append(f"- {f.severity} {f.package} ({f.manifest}), open {f.days_open} days: {f.status} {f.url}")
    return "\n".join(lines)


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPOSITORY"]
    webhook = os.environ["SLACK_ALERTS_WEBHOOK"]
    now = datetime.datetime.now(datetime.timezone.utc)

    alerts = github(f"/repos/{repo}/dependabot/alerts?state=open&severity=high,critical&per_page=100", token)
    prs = [
        pr for pr in github(f"/repos/{repo}/pulls?state=open&per_page=100", token) if pr["user"]["login"] == DEPENDABOT
    ]

    findings = []
    for alert in alerts:
        matched = pr_for(alert, prs)
        if matched is None:
            findings.append(finding(alert, "no Dependabot PR", True, now))
            continue
        pr, match = matched
        sha = pr["head"]["sha"]
        check_runs = github(f"/repos/{repo}/commits/{sha}/check-runs?per_page=100", token)["check_runs"]
        mergeable_state = github(f"/repos/{repo}/pulls/{pr['number']}", token).get("mergeable_state", "")
        findings.append(finding(alert, *pr_status(pr, match, check_runs, mergeable_state), now))

    heartbeat = now.weekday() == 0 or os.environ.get("EVENT_NAME") == "workflow_dispatch"
    text = message(findings, heartbeat)
    if text:
        request = urllib.request.Request(
            webhook, data=json.dumps({"Content": text}).encode(), headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(request, timeout=30).close()
    print(f"open={len(findings)} need_person={sum(f.needs_person for f in findings)} posted={bool(text)}")


if __name__ == "__main__":
    main()
