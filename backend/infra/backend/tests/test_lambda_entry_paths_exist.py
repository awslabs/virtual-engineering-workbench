"""Every Lambda entry path declared in infra must point at a real handler package.

A stack can declare an `entry=` that no longer exists in `app/` — the Python is valid,
the unit tests that only inspect a template still pass, and the failure surfaces at
`cdk synth`/`cdk deploy` when bundling tries to read the directory. This check is static
on purpose: it costs nothing, needs no synth, and covers every stack at once.
"""

import pathlib
import re

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
INFRA_DIR = BACKEND_ROOT / "infra"

_ENTRY = re.compile(r"""entry\s*=\s*["'](app/[^"']+)["']""")

# Pre-existing on mainline, not introduced by the change that added this check.
# ProjectsAppStack declares a domain_event_handler Lambda whose package was never added
# to app/projects/entrypoints/. Left failing-but-expected so the check can ship without
# silently widening this PR's scope; needs its own fix (delete the entry point, or add
# the handler). strict=True makes the xfail an error once it is fixed, so this list
# cannot rot.
KNOWN_MISSING = {"app/projects/entrypoints/domain_event_handler"}


def _declared_entries() -> list[tuple[pathlib.Path, int, str]]:
    found = []
    for source in sorted(INFRA_DIR.rglob("*.py")):
        if "tests" in source.parts:
            continue
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            for match in _ENTRY.finditer(line):
                found.append((source, lineno, match.group(1)))
    return found


def _params():
    params = []
    for source, lineno, entry in _declared_entries():
        marks = [pytest.mark.xfail(reason=f"known missing handler package: {entry}", strict=True)] if entry in KNOWN_MISSING else []
        params.append(pytest.param(source, lineno, entry, marks=marks, id=f"{source.name}:{lineno}:{entry}"))
    return params


def test_the_scan_finds_entry_declarations():
    """Guard the regex itself: an empty result would make the test below vacuous."""
    assert len(_declared_entries()) > 5


@pytest.mark.parametrize("source,lineno,entry", _params())
def test_declared_lambda_entry_directory_exists(source, lineno, entry):
    path = BACKEND_ROOT / entry
    assert path.is_dir(), (
        f"{source.relative_to(BACKEND_ROOT)}:{lineno} declares entry={entry!r}, "
        f"but {path} does not exist. Bundling this Lambda fails at synth."
    )
