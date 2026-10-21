#!/usr/bin/env python3
"""Summarise `cdk diff` output as one table.

A diff across VEW's CDK apps runs to hundreds of thousands of characters, and
cdk reports "Number of stacks with differences" once per app rather than once
per run, so the figure printed last is not the total. This reads the captured
output and answers the two questions that decide whether an upgrade is routine:
how much changes, and whether anything holding data is replaced or removed.

cdk's text output is not a stable interface, so this refuses to print rather
than report a reassuring total it is no longer parsing correctly. See
verify() for the checks.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Replacing or removing one of these loses data. Everything else a deploy
# recreates for free.
STATEFUL = re.compile(
    r"AWS::(?:DynamoDB::Table|S3::Bucket|Cognito::UserPool"
    r"|RDS::\w+|EFS::\w+|OpenSearchService::\w+|Elasticsearch::\w+"
    r"|DocDB::\w+|Neptune::\w+|MemoryDB::\w+|ElastiCache::\w+)"
)

# "Stack Logical (physical-name) (aws://account/region)", or without the
# physical name for a stack whose id cdk could not resolve.
STACK = re.compile(r"^Stack (\S+?)(?: \((\S+?)\))? \(aws://")
COUNT = re.compile(r"Number of stacks with differences:\s*(\d+)")
NO_DIFF = re.compile(r"^There were no differences\b")
CHANGE = re.compile(r"^\[([+~-])\] (\S+)")
REPLACED = re.compile(r"may be replaced|requires replacement")
IAM_BLOCK = re.compile(r"^(?:IAM Statement Changes|IAM Policy Changes|Security Group Changes)")


@dataclass
class Stack:
    name: str
    added: int = 0
    updated: int = 0
    removed: int = 0
    replaced: int = 0
    iam: int = 0
    stateful: list[str] = field(default_factory=list)
    orphaned: int = 0
    destroyed: int = 0
    unchanged: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.added or self.updated or self.removed)


def parse(text: str) -> tuple[list[Stack], list[int]]:
    stacks: list[Stack] = []
    counts: list[int] = []
    current: Stack | None = None

    for raw in text.splitlines():
        line = ANSI.sub("", raw).rstrip()

        found = COUNT.search(line)
        if found:
            counts.append(int(found.group(1)))
            continue

        header = STACK.match(line)
        if header:
            current = Stack(name=header.group(2) or header.group(1))
            stacks.append(current)
            continue

        if current is None:
            continue

        if NO_DIFF.match(line):
            current.unchanged = True
            continue

        change = CHANGE.match(line)
        if change:
            verb, resource_type = change.groups()
            if verb == "+":
                current.added += 1
            elif verb == "~":
                current.updated += 1
            else:
                current.removed += 1
                # cdk marks a removal "orphan" when the resource is retained
                # and "destroy" when it actually goes.
                if line.endswith("orphan"):
                    current.orphaned += 1
                elif line.endswith("destroy"):
                    current.destroyed += 1
                if STATEFUL.search(resource_type):
                    current.stateful.append(f"removed {resource_type}")

        if REPLACED.search(line):
            current.replaced += 1
            if STATEFUL.search(line):
                current.stateful.append(f"replaced {STATEFUL.search(line).group(0)}")

        if IAM_BLOCK.match(line):
            current.iam += 1

    return stacks, counts


def verify(text: str, stacks: list[Stack], counts: list[int]) -> str | None:
    """Return why the summary cannot be trusted, or None if it can.

    cdk's own per-app totals are the checksum: if they disagree with what was
    parsed, the format has moved and every other number here is suspect.
    """
    if not text.strip():
        return "the diff output was empty"
    if not stacks:
        return "no stack headers found — cdk's output format has changed"
    if not counts:
        return "cdk reported no stack totals — its output format has changed"

    changed = sum(1 for s in stacks if s.changed)
    if changed != sum(counts):
        return (
            f"parsed {changed} changed stack(s) but cdk reported "
            f"{sum(counts)} across {len(counts)} app(s)"
        )
    return None


def render(stacks: list[Stack]) -> str:
    changed = [s for s in stacks if s.changed]
    unchanged = [s for s in stacks if not s.changed]
    width = max([len(s.name) for s in changed] + [len("Stack")])

    rows = [
        f"{'Stack'.ljust(width)}    +     ~     -   replace   IAM   stateful",
        "-" * (width + 46),
    ]
    # Anything touching data first, then by how much moves.
    for s in sorted(changed, key=lambda s: (-len(s.stateful), -s.replaced, -s.updated)):
        rows.append(
            f"{s.name.ljust(width)} {s.added:>4}  {s.updated:>4}  {s.removed:>4}   "
            f"{s.replaced:>7}   {s.iam or '-':>3}   {len(s.stateful) or '-':>8}"
        )
    rows.append("-" * (width + 46))

    at_risk = [(s, d) for s in changed for d in s.stateful]
    total_replaced = sum(s.replaced for s in changed)
    rows.append(
        f"{len(changed)} stack(s) with differences, {len(unchanged)} unchanged "
        f"· {total_replaced} replacement(s)"
    )
    rows.append(
        f"removals: {sum(s.orphaned for s in changed)} orphaned (retained), "
        f"{sum(s.destroyed for s in changed)} destroyed"
    )

    if at_risk:
        rows.append("")
        rows.append("DATA AT RISK — these hold data and would be replaced or removed:")
        for stack, detail in at_risk:
            rows.append(f"  {stack.name}: {detail}")
    else:
        rows.append("No resource holding data is replaced or removed.")

    return "\n".join(rows)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: diff-summary.py <captured-cdk-diff>", file=sys.stderr)
        return 2

    try:
        with open(argv[1], encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"could not read {argv[1]}: {exc}", file=sys.stderr)
        return 2

    stacks, counts = parse(text)
    problem = verify(text, stacks, counts)
    if problem:
        print(f"Could not summarise the diff: {problem}.", file=sys.stderr)
        print("The full output above is unaffected.", file=sys.stderr)
        return 1

    print(render(stacks))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
