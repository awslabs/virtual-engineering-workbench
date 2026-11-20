#!/usr/bin/env python3
"""Check that Dependabot and CI cover every dependency file in the repository.

Reads the tracked files (git ls-files), .github/dependabot.yml,
backend/scripts/compile.sh, backend/pyproject.toml, the Lambda requirements.in
files and the workflows under .github/workflows. It fails when:

- a tracked manifest or lockfile has no dependabot.yml entry of its ecosystem,
  or an entry lists a directory that holds no such file;
- an entry has no schedule, no cooldown or no positive open-pull-requests-limit,
  or a uv or npm entry doesn't use versioning-strategy "increase";
- the tracked Lambda requirements.in files and REQUIREMENTS_FILES in
  backend/scripts/compile.sh differ;
- a direct Python requirement in backend/pyproject.toml or a Lambda
  requirements.in uses a three-part compatible-release pin (~=X.Y.Z), which
  blocks the next minor release;
- a pinned dependency file has a name GitHub's dependency graph doesn't read
  and UNINDEXED doesn't name it;
- a workflow "uses:" comment isn't a full version such as "# v4.3.1", which
  Dependabot needs to keep the comment in step with the pinned SHA;
- an exemption below names something that no longer needs it.

The exemption tables name each exempt file with its reason.

Exit codes: 0 clean, 1 failures, 2 the check could not run.
Standard library only, Python 3.13 or later.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

DEPENDABOT = ".github/dependabot.yml"
COMPILE_SH = "backend/scripts/compile.sh"
PYPROJECT = "backend/pyproject.toml"

USECASE_DIR = "backend/infra/backend/resources/projects_app_stack/usecase_cdk_app"

# Files with no dependabot.yml entry of their ecosystem.
NOT_UPDATED: dict[str, str] = {
    "frontend/requirements.txt": (
        "Input of frontend/requirements.lock, a name Dependabot doesn't pair with it, so an update would leave the "
        "lock behind; it joins the uv entry once renamed to requirements.in."
    ),
    f"{USECASE_DIR}/requirements.txt": (
        "Version ranges with no lock; it joins the uv entry once a requirements.in compiles it to a hashed lock."
    ),
}

# Pinned files under a name GitHub's dependency graph doesn't read, so no Dependabot alert covers them. A file
# that a ci.yml step audits instead goes here with that step named in its reason.
UNINDEXED: dict[str, str] = {
    "Dockerfile": "Base image pinned by digest and kept current by the docker entry; the dependency graph doesn't "
    "read Dockerfiles.",
    f"{USECASE_DIR}/Dockerfile": "Base image pinned by digest and kept current by the docker entry; the dependency "
    "graph doesn't read Dockerfiles.",
    "frontend/requirements.lock": "Hashed uv pip compile output that no ci.yml step audits; it becomes "
    "frontend/requirements.txt.",
}

_PIN_REASON = "Relaxing it changes resolved versions, so it needs its own change and tests."

# Three-part ~= pins, by file and normalized package name.
PIN_EXEMPT: dict[tuple[str, str], str] = {
    **{
        (PYPROJECT, name): _PIN_REASON
        for name in (
            "aws-cdk-lib",
            "aws-cdk-aws-glue-alpha",
            "aws-cdk-aws-lambda-python-alpha",
            "aws-cdk-aws-pipes-alpha",
            "aws-cdk-aws-pipes-sources-alpha",
            "aws-cdk-aws-pipes-targets-alpha",
            "cdk-monitoring-constructs",
            "cdk-nag",
            "constructs",
            "typeguard",
            "pyyaml",
            "semver",
            "urllib3",
            "aws-durable-execution-sdk-python-testing",
            "black",
            "gitpython",
            "hypothesis",
            "openapi-spec-validator",
            "pygments",
            "pytest",
        )
    },
    ("backend/app/packaging/libraries/requirements.in", "natsort"): _PIN_REASON,
    ("backend/app/packaging/libraries/requirements.in", "pyyaml"): _PIN_REASON,
    ("backend/app/packaging/libraries/requirements.in", "semver"): _PIN_REASON,
    ("backend/app/provisioning/libraries/requirements.in", "semver"): _PIN_REASON,
}

# Actions whose "uses:" comment can't be a full version.
ACTION_EXEMPT: dict[str, str] = {
    "dtolnay/rust-toolchain": "Publishes no full-version release tags; pinned to a commit of its default branch.",
}

REQUIREMENTS_NAME = re.compile(r"^requirements[\w.-]*\.(?:txt|in)$")
INDEXED_NAMES = frozenset({"Cargo.lock", "go.mod", "package-lock.json", "uv.lock", "yarn.lock"})
VERSIONING_STRATEGY = {"uv": "increase", "npm": "increase"}
FULL_VERSION = re.compile(r"v?\d+\.\d+\.\d+(?:\s|$)")
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>[^\s#]+)\s*(?:#\s*(?P<comment>.*))?$")
THREE_PART_PIN = re.compile(r"~=\s*(\d+\.\d+\.\d+\S*)")
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


class CheckError(Exception):
    """The check could not run."""


# The YAML subset this parser reads: block mappings and sequences, flow sequences of scalars, quoted and plain
# scalars, and comments. Anything else (anchors, aliases, tags, flow mappings, block scalars, multi-line plain
# scalars, tabs) is refused, so a construct this parser can't read stops the check instead of being misread.


@dataclass
class _Line:
    number: int
    indent: int
    text: str


class _YamlSubset:
    def __init__(self, text: str, source: str) -> None:
        self.raw = text.splitlines()
        self.pos = 0
        self.source = source

    def error(self, number: int, message: str) -> CheckError:
        return CheckError(f"{self.source}:{number}: {message}")

    def peek(self) -> _Line | None:
        while self.pos < len(self.raw):
            raw = self.raw[self.pos]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.pos += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if raw[indent] == "\t":
                raise self.error(self.pos + 1, "tab indentation is not supported")
            if stripped in ("---", "..."):
                raise self.error(self.pos + 1, "document markers are not supported")
            return _Line(self.pos + 1, indent, _strip_comment(raw[indent:]).rstrip())
        return None

    def parse(self) -> Any:
        line = self.peek()
        if line is None:
            return None
        value = self.node(line)
        rest = self.peek()
        if rest is not None:
            raise self.error(rest.number, "unexpected indentation")
        return value

    def node(self, line: _Line) -> Any:
        if _is_item(line.text):
            return self.sequence(line.indent)
        return self.mapping(line.indent)

    def sequence(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while (line := self.peek()) is not None and line.indent == indent and _is_item(line.text):
            rest = line.text[1:].lstrip()
            if not rest:
                self.pos += 1
                child = self.peek()
                if child is None or child.indent <= indent:
                    items.append(None)
                else:
                    items.append(self.node(child))
            elif _split_key(rest) is not None:
                items.append(self.mapping(indent + len(line.text) - len(rest), first=rest))
            else:
                self.pos += 1
                items.append(self.scalar(rest, line.number))
        if line is not None and line.indent > indent:
            raise self.error(line.number, "unexpected indentation")
        return items

    def mapping(self, indent: int, first: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while True:
            if first is not None:
                line = _Line(self.pos + 1, indent, first)
                first = None
            else:
                peeked = self.peek()
                if peeked is None or peeked.indent < indent or (peeked.indent == indent and _is_item(peeked.text)):
                    break
                if peeked.indent > indent:
                    raise self.error(peeked.number, "unexpected indentation")
                line = peeked
            self.pos += 1
            split = _split_key(line.text)
            if split is None:
                raise self.error(line.number, "expected a 'key: value' line")
            key, value = split
            if key in result:
                raise self.error(line.number, f"duplicate key {key!r}")
            if value == "":
                child = self.peek()
                if child is not None and (child.indent > indent or (child.indent == indent and _is_item(child.text))):
                    result[key] = self.node(child)
                else:
                    result[key] = None
            else:
                result[key] = self.scalar(value, line.number)
        return result

    def scalar(self, text: str, number: int) -> Any:
        if text[0] in "&*!{|>%@`":
            raise self.error(number, f"unsupported YAML construct {text!r}")
        if text.startswith("["):
            if not text.endswith("]"):
                raise self.error(number, "a flow sequence must close on its line")
            inner = text[1:-1].strip()
            return [self.scalar(part.strip(), number) for part in _split_flow(inner)] if inner else []
        if text.startswith('"'):
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise self.error(number, f"bad double-quoted scalar: {exc}") from exc
            return value
        if text.startswith("'"):
            if len(text) < 2 or not text.endswith("'"):
                raise self.error(number, "unterminated single-quoted scalar")
            return text[1:-1].replace("''", "'")
        if text in ("true", "false"):
            return text == "true"
        if text in ("null", "~"):
            return None
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        return text


def _is_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _strip_comment(text: str) -> str:
    quote = None
    for i, char in enumerate(text):
        if quote:
            if char == quote and not (quote == '"' and text[i - 1] == "\\"):
                quote = None
        elif char in "\"'" and (i == 0 or text[i - 1] in " [,:"):
            quote = char
        elif char == "#" and (i == 0 or text[i - 1] == " "):
            return text[:i]
    return text


def _split_key(text: str) -> tuple[str, str] | None:
    if text[0] in "\"'":
        end = text.find(text[0], 1)
        if end < 0 or not text[end + 1 :].startswith(":"):
            return None
        key, rest = text[1:end], text[end + 2 :]
    else:
        match = re.match(r"([^\s:#\[\]{},\"'][^:#]*?):(?:\s|$)", text)
        if match is None:
            return None
        key, rest = match.group(1), text[match.end() :]
    return key, rest.strip()


def _split_flow(text: str) -> list[str]:
    parts, current, quote = [], "", None
    for char in text:
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char in "[]{}":
            raise CheckError(f"nested flow collection in [{text}]")
        elif char == ",":
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    return parts


def parse_yaml(text: str, source: str) -> Any:
    return _YamlSubset(text, source).parse()


def tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CheckError(f"git ls-files failed in {root}: {exc}") from exc
    return [path for path in result.stdout.split("\0") if path]


def read(root: Path, path: str) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"cannot read {path}: {exc}") from exc


def ecosystems_of(path: str) -> frozenset[str]:
    """Return the dependabot.yml ecosystems that can update this file, or an empty set."""
    name = posixpath.basename(path)
    if path.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return frozenset({"github-actions"})
    if name == ".pre-commit-config.yaml":
        return frozenset({"pre-commit"})
    if name in ("package.json", "package-lock.json", "yarn.lock"):
        return frozenset({"npm"})
    if name in ("pyproject.toml", "uv.lock") or REQUIREMENTS_NAME.match(name):
        return frozenset({"uv", "pip"})
    if name in ("Cargo.toml", "Cargo.lock"):
        return frozenset({"cargo"})
    if name in ("go.mod", "go.sum"):
        return frozenset({"gomod"})
    if _is_dockerfile(name):
        return frozenset({"docker"})
    return frozenset()


def _is_dockerfile(name: str) -> bool:
    return name == "Dockerfile" or name.startswith("Dockerfile.") or name.endswith(".Dockerfile")


def manifest_directory(path: str) -> str:
    if path.startswith(".github/workflows/"):
        return "/"
    return "/" + posixpath.dirname(path)


def normalize_directory(directory: str) -> str:
    return "/" + directory.strip("/")


def directory_matches(pattern: str, directory: str) -> bool:
    return PurePosixPath(directory).full_match(pattern)


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class Entry:
    ecosystem: str
    directories: list[str]
    settings: dict[str, Any]


def read_entries(config: Any) -> tuple[list[Entry], list[str]]:
    failures: list[str] = []
    if not isinstance(config, dict) or not isinstance(config.get("updates"), list):
        return [], [f"{DEPENDABOT}: no 'updates' list"]
    entries = []
    for number, update in enumerate(config["updates"], start=1):
        if not isinstance(update, dict) or not isinstance(update.get("package-ecosystem"), str):
            failures.append(f"{DEPENDABOT}: update {number} has no package-ecosystem")
            continue
        listed = update.get("directories", [update.get("directory")] if "directory" in update else [])
        if not isinstance(listed, list) or not listed or not all(isinstance(item, str) for item in listed):
            failures.append(f"{DEPENDABOT}: {update['package-ecosystem']} entry has no directories")
            listed = []
        entries.append(Entry(update["package-ecosystem"], [normalize_directory(item) for item in listed], update))
    return entries, failures


def is_count(value: object) -> TypeGuard[int]:
    """True for an int that isn't a bool; YAML true and false parse to bool, which is an int subclass."""
    return isinstance(value, int) and not isinstance(value, bool)


def check_entry_settings(entries: list[Entry]) -> list[str]:
    failures = []
    for entry in entries:
        name = f"{DEPENDABOT}: {entry.ecosystem} entry"
        schedule = entry.settings.get("schedule")
        if not isinstance(schedule, dict) or not schedule.get("interval"):
            failures.append(f"{name} has no schedule interval")
        cooldown = entry.settings.get("cooldown")
        if not isinstance(cooldown, dict) or not is_count(cooldown.get("default-days")):
            failures.append(f"{name} has no cooldown default-days")
        limit = entry.settings.get("open-pull-requests-limit")
        if not is_count(limit) or limit < 1:
            failures.append(f"{name} needs an open-pull-requests-limit of 1 or more, has {limit!r}")
        wanted = VERSIONING_STRATEGY.get(entry.ecosystem)
        if wanted and entry.settings.get("versioning-strategy") != wanted:
            failures.append(
                f"{name} needs versioning-strategy {wanted!r}, has {entry.settings.get('versioning-strategy')!r}"
            )
    return failures


def check_coverage(files: list[str], entries: list[Entry]) -> list[str]:
    failures = []
    manifests = {path: ecosystems_of(path) for path in files if ecosystems_of(path)}
    for path, ecosystems in sorted(manifests.items()):
        directory = manifest_directory(path)
        covered = any(
            entry.ecosystem in ecosystems
            and any(directory_matches(pattern, directory) for pattern in entry.directories)
            for entry in entries
        )
        if path in NOT_UPDATED:
            if covered:
                failures.append(f"{path}: exempt in NOT_UPDATED, but a dependabot.yml entry now covers it")
        elif not covered:
            failures.append(f"{path}: no {' or '.join(sorted(ecosystems))} entry in {DEPENDABOT} covers {directory}")
    for entry in entries:
        for pattern in entry.directories:
            if not any(
                entry.ecosystem in ecosystems and directory_matches(pattern, manifest_directory(path))
                for path, ecosystems in manifests.items()
            ):
                failures.append(f"{DEPENDABOT}: {entry.ecosystem} entry lists {pattern}, which holds no such manifest")
    for path in sorted(NOT_UPDATED):
        if path not in manifests:
            failures.append(f"{path}: exempt in NOT_UPDATED, but no such manifest is tracked")
    return failures


def lambda_requirements(files: list[str]) -> list[str]:
    return sorted(path for path in files if path.startswith("backend/") and path.endswith("/requirements.in"))


def compile_sh_requirements(text: str) -> list[str] | None:
    match = re.search(r"^REQUIREMENTS_FILES=\(\n(.*?)^\)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return None
    entries = [line.split("#", 1)[0].strip() for line in match.group(1).splitlines()]
    return ["backend/" + entry for entry in entries if entry]


def check_compile_sh(files: list[str], root: Path) -> list[str]:
    if COMPILE_SH not in files:
        return [f"{COMPILE_SH}: not tracked"]
    listed = compile_sh_requirements(read(root, COMPILE_SH))
    if listed is None:
        return [f"{COMPILE_SH}: no REQUIREMENTS_FILES=( ... ) list"]
    tracked = lambda_requirements(files)
    failures = [f"{path}: not listed in REQUIREMENTS_FILES of {COMPILE_SH}" for path in tracked if path not in listed]
    failures += [f"{COMPILE_SH}: lists {path}, which is not tracked" for path in listed if path not in tracked]
    return failures


def pyproject_requirements(text: str) -> list[str]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise CheckError(f"{PYPROJECT}: {exc}") from exc
    project = data.get("project", {})
    requirements = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        requirements += group
    for group in data.get("dependency-groups", {}).values():
        requirements += [item for item in group if isinstance(item, str)]
    return requirements


def requirements_in_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            lines.append(line)
    return lines


def check_pins(files: list[str], root: Path) -> list[str]:
    sources: dict[str, list[str]] = {}
    if PYPROJECT in files:
        sources[PYPROJECT] = pyproject_requirements(read(root, PYPROJECT))
    for path in lambda_requirements(files):
        sources[path] = requirements_in_lines(read(root, path))
    failures: list[str] = []
    found: set[tuple[str, str]] = set()
    for path, requirements in sources.items():
        for requirement in requirements:
            pin = THREE_PART_PIN.search(requirement)
            name = REQUIREMENT_NAME.match(requirement)
            if pin is None or name is None:
                continue
            key = (path, normalize_name(name.group(1)))
            found.add(key)
            if key not in PIN_EXEMPT:
                failures.append(
                    f"{path}: {name.group(1)} is pinned ~={pin.group(1)}, which blocks the next minor release; "
                    "use ~=X.Y or >=X.Y.Z,<next major"
                )
    for exempt_path, exempt_name in sorted(set(PIN_EXEMPT) - found):
        failures.append(f"{exempt_path}: {exempt_name} is exempt in PIN_EXEMPT, but no longer has a three-part ~= pin")
    return failures


def is_indexed(name: str) -> bool:
    return name in INDEXED_NAMES or (REQUIREMENTS_NAME.match(name) is not None and name.endswith(".txt"))


def is_pinned_file(name: str) -> bool:
    return is_indexed(name) or name.endswith(".lock") or _is_dockerfile(name)


def check_unindexed(files: list[str]) -> list[str]:
    failures = []
    pinned = {path for path in files if is_pinned_file(posixpath.basename(path))}
    for path in sorted(pinned):
        if not is_indexed(posixpath.basename(path)) and path not in UNINDEXED:
            failures.append(
                f"{path}: GitHub's dependency graph doesn't read this file name, so no alert covers it; rename it or "
                "add it to UNINDEXED with the reason, such as the ci.yml step that audits it"
            )
    for path in sorted(set(UNINDEXED) - pinned):
        failures.append(f"{path}: exempt in UNINDEXED, but no such file is tracked")
    return failures


def check_action_comments(files: list[str], root: Path) -> list[str]:
    failures, used = [], set()
    workflows = [path for path in files if ecosystems_of(path) == {"github-actions"}]
    for path in sorted(workflows):
        for number, line in enumerate(read(root, path).splitlines(), start=1):
            match = USES_LINE.match(line)
            if match is None:
                continue
            ref = match.group("ref").strip("\"'")
            if ref.startswith(("./", "docker://")):
                continue
            action = "/".join(ref.split("@", 1)[0].split("/")[:2])
            used.add(action)
            comment = (match.group("comment") or "").strip()
            if action not in ACTION_EXEMPT and not FULL_VERSION.match(comment):
                failures.append(
                    f"{path}:{number}: {action} comment {comment!r} isn't a full version such as 'v4.3.1', "
                    "so Dependabot won't update it with the SHA"
                )
    for action in sorted(set(ACTION_EXEMPT) - used):
        failures.append(f"{action}: exempt in ACTION_EXEMPT, but no workflow uses it")
    return failures


def run_checks(root: Path) -> list[str]:
    files = tracked_files(root)
    if DEPENDABOT not in files:
        return [f"{DEPENDABOT}: not tracked"]
    entries, failures = read_entries(parse_yaml(read(root, DEPENDABOT), DEPENDABOT))
    failures += check_entry_settings(entries)
    failures += check_coverage(files, entries)
    failures += check_compile_sh(files, root)
    failures += check_pins(files, root)
    failures += check_unindexed(files)
    failures += check_action_comments(files, root)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent, help="repository root (default: this one)"
    )
    args = parser.parse_args(argv)
    try:
        failures = run_checks(args.root)
    except CheckError as exc:
        print(f"Dependency coverage check could not run: {exc}", file=sys.stderr)
        return 2
    for failure in failures:
        print(failure)
    if failures:
        print(f"Dependency coverage: {len(failures)} failure(s).", file=sys.stderr)
        return 1
    print("Dependency coverage: clean.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
