"""Tests for scripts/check-dependency-coverage.py.

Each test copies the repository's dependency files, workflows and
dependabot.yml from the working tree into a fresh git repository, changes one
thing and runs the check against that copy.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-dependency-coverage.py"

FIXTURE_FILE = re.compile(
    r"^\.github/"
    r"|^backend/scripts/compile\.sh$"
    r"|(^|/)(package(-lock)?\.json|[^/]*\.lock|pyproject\.toml|requirements[^/]*\.(txt|in)|Cargo\.toml|go\.(mod|sum)"
    r"|Dockerfile[^/]*|\.pre-commit-config\.yaml)$"
)
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

AUDIT_STEP = """\
      - name: Audit the tools lock
        working-directory: frontend/tools
        run: uvx pip-audit -r requirements.lock

"""


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True, check=True).stdout


class CoverageCheckTest(unittest.TestCase):
    files: list[str]

    @classmethod
    def setUpClass(cls) -> None:
        tracked = git(REPO_ROOT, "ls-files", "-z").split("\0")
        cls.files = [path for path in tracked if path and FIXTURE_FILE.search(path) and (REPO_ROOT / path).is_file()]

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="coverage-check-"))
        self.addCleanup(shutil.rmtree, self.root)
        for path in self.files:
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / path, self.root / path)
        git(self.root, "init", "-q")

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text, encoding="utf-8")

    def edit(self, path: str, old: str, new: str, after: str = "") -> None:
        """Replace the first "old" in the file that comes after the first "after"."""
        text = (self.root / path).read_text(encoding="utf-8")
        start = text.index(after) if after else 0
        at = text.index(old, start)
        self.write(path, text[:at] + new + text[at + len(old) :])

    def run_check(self, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        if root is None:
            git(self.root, "add", "-A")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root or self.root)], capture_output=True, text=True, check=False
        )

    def assert_failures(self, *expected: str) -> None:
        """Assert exit 1 with exactly one failure line per expected fragment, in order."""
        result = self.run_check()
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(lines), len(expected), result.stdout)
        for line, fragment in zip(lines, expected):
            self.assertIn(fragment, line)

    def test_repository_tree_passes(self) -> None:
        result = self.run_check(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")

    def test_copied_tree_passes(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fails_when_a_lambda_directory_leaves_dependabot(self) -> None:
        self.edit(".github/dependabot.yml", '      - "/backend/app/shared"\n', "")
        self.assert_failures(
            "backend/app/shared/requirements.in: no pip or uv entry",
            "backend/app/shared/requirements.txt: no pip or uv entry",
        )

    def test_fails_when_compile_sh_misses_a_requirements_in(self) -> None:
        self.write("backend/app/widgets/libraries/requirements.in", "boto3\n")
        self.assert_failures("backend/app/widgets/libraries/requirements.in: not listed in REQUIREMENTS_FILES")

    def test_fails_when_compile_sh_lists_an_untracked_file(self) -> None:
        self.edit(
            "backend/scripts/compile.sh",
            "    app/shared/requirements.in\n",
            "    app/shared/requirements.in\n    app/gone/requirements.in\n",
        )
        self.assert_failures("lists backend/app/gone/requirements.in, which is not tracked")

    def test_fails_when_a_package_json_has_no_npm_entry(self) -> None:
        self.write("frontend/widgets/package.json", "{}\n")
        self.assert_failures("frontend/widgets/package.json: no npm entry")

    def test_fails_when_pre_commit_config_has_no_entry(self) -> None:
        text = (self.root / ".github/dependabot.yml").read_text(encoding="utf-8")
        self.write(".github/dependabot.yml", text[: text.index('  - package-ecosystem: "pre-commit"')])
        self.assert_failures(".pre-commit-config.yaml: no pre-commit entry")

    def test_fails_when_an_entry_lists_a_directory_without_manifests(self) -> None:
        self.edit(
            ".github/dependabot.yml",
            '      - "/backend/app/shared"\n',
            '      - "/backend/app/shared"\n      - "/backend/app/gone"\n',
        )
        self.assert_failures("uv entry lists /backend/app/gone, which holds no such manifest")

    def test_fails_on_a_three_part_pin_in_a_lambda_requirements_in(self) -> None:
        path = "backend/app/authorization/libraries/requirements.in"
        self.write(path, (self.root / path).read_text(encoding="utf-8") + "requests ~= 2.32.3\n")
        self.assert_failures(f"{path}: requests is pinned ~=2.32.3")

    def test_fails_when_an_exempt_pin_is_relaxed(self) -> None:
        self.edit("backend/app/packaging/libraries/requirements.in", "pyyaml ~= 6.0.1", "pyyaml ~= 6.0")
        self.assert_failures("backend/app/packaging/libraries/requirements.in: pyyaml is exempt in PIN_EXEMPT")

    def test_fails_when_the_uv_entry_has_no_versioning_strategy(self) -> None:
        self.edit(
            ".github/dependabot.yml", '    versioning-strategy: "increase"\n', "", after='package-ecosystem: "uv"'
        )
        self.assert_failures("uv entry needs versioning-strategy 'increase', has None")

    def test_fails_when_an_entry_has_no_cooldown(self) -> None:
        self.edit(
            ".github/dependabot.yml",
            "    cooldown:\n      default-days: 7\n      semver-major-days: 30\n",
            "",
            after='package-ecosystem: "cargo"',
        )
        self.assert_failures("cargo entry has no cooldown default-days")

    def test_fails_when_an_entry_has_no_schedule(self) -> None:
        schedule = '    schedule:\n      interval: "weekly"\n      day: "monday"\n      time: "06:00"\n'
        self.edit(
            ".github/dependabot.yml",
            schedule + '      timezone: "Europe/Zurich"\n',
            "",
            after='package-ecosystem: "github-actions"',
        )
        self.assert_failures("github-actions entry has no schedule interval")

    def test_fails_when_an_entry_turns_off_version_updates(self) -> None:
        self.edit(
            ".github/dependabot.yml",
            "open-pull-requests-limit: 5",
            "open-pull-requests-limit: 0",
            after='package-ecosystem: "docker"',
        )
        self.assert_failures("docker entry needs an open-pull-requests-limit of 1 or more, has 0")

    def test_fails_when_the_pull_request_limit_is_a_boolean(self) -> None:
        self.edit(
            ".github/dependabot.yml",
            "open-pull-requests-limit: 5",
            "open-pull-requests-limit: true",
            after='package-ecosystem: "docker"',
        )
        self.assert_failures("docker entry needs an open-pull-requests-limit of 1 or more, has True")

    def test_fails_when_cooldown_days_is_a_boolean(self) -> None:
        self.edit(".github/dependabot.yml", "default-days: 7", "default-days: true", after='package-ecosystem: "npm"')
        self.assert_failures("npm entry has no cooldown default-days")

    def test_fails_on_a_lock_file_the_dependency_graph_does_not_read(self) -> None:
        self.write("frontend/tools/requirements.lock", "awscli==1.44.70\n")
        self.assert_failures("frontend/tools/requirements.lock: GitHub's dependency graph doesn't read")

    def test_fails_on_an_unindexed_lock_file_that_ci_audits(self) -> None:
        self.write("frontend/tools/requirements.lock", "awscli==1.44.70\n")
        self.edit(".github/workflows/ci.yml", "      - name: Unit tests\n", AUDIT_STEP + "      - name: Unit tests\n")
        self.assert_failures("frontend/tools/requirements.lock: GitHub's dependency graph doesn't read")

    def test_fails_when_an_exempt_file_is_gone(self) -> None:
        (self.root / "frontend/requirements.lock").unlink()
        self.assert_failures("frontend/requirements.lock: exempt in UNINDEXED, but no such file is tracked")

    def test_fails_when_an_update_exempt_manifest_is_gone(self) -> None:
        (self.root / "frontend/requirements.txt").unlink()
        self.assert_failures("frontend/requirements.txt: exempt in NOT_UPDATED, but no such manifest is tracked")

    def test_fails_when_an_update_exempt_manifest_gains_an_entry(self) -> None:
        self.edit(
            ".github/dependabot.yml",
            '      - "/backend/app/shared"\n',
            '      - "/backend/app/shared"\n      - "/frontend"\n',
        )
        self.assert_failures(
            "frontend/requirements.txt: exempt in NOT_UPDATED, but a dependabot.yml entry now covers it"
        )

    def test_fails_when_an_entry_has_no_directories(self) -> None:
        self.edit(".github/dependabot.yml", '    directory: "/cli"\n', "")
        self.assert_failures(
            "cargo entry has no directories",
            "cli/Cargo.lock: no cargo entry",
            "cli/Cargo.toml: no cargo entry",
        )

    def test_fails_on_a_major_only_action_comment(self) -> None:
        self.edit(".github/workflows/ci.yml", "# v4.3.1", "# v4")
        self.assert_failures(".github/workflows/ci.yml:24: actions/checkout comment 'v4' isn't a full version")

    def test_fails_on_an_action_without_a_version_comment(self) -> None:
        self.edit(".github/workflows/scorecard.yml", " # v2.4.2", "")
        self.assert_failures("ossf/scorecard-action comment '' isn't a full version")

    def test_fails_when_an_exempt_action_is_unused(self) -> None:
        self.edit(
            ".github/workflows/cli.yml",
            "dtolnay/rust-toolchain@2c7215f132e9ebf062739d9130488b56d53c060c # master, 2026-07-16",
            "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1",
        )
        self.assert_failures("dtolnay/rust-toolchain: exempt in ACTION_EXEMPT, but no workflow uses it")

    def test_refuses_yaml_it_cannot_read(self) -> None:
        self.edit(".github/dependabot.yml", "    schedule:\n", "    schedule: &weekly\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unsupported YAML construct", result.stderr)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], "-v", *sys.argv[1:]])
