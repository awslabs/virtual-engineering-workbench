"""Every boto3 type-stub module a Lambda imports at runtime must ship in its layers.

The code base imports mypy_boto3_* clients at module level, so they are runtime
dependencies, not just type hints. The dev virtualenv has every stub installed,
so a missing layer pin passes all unit tests and only fails when the deployed
function initialises (Runtime.ImportModuleError). A bounded context's Lambdas get
its own libraries layer plus the shared layer, so each runtime import in
app/<context> or app/shared must be pinned in one of those two lockfiles.
Imports under `if TYPE_CHECKING:` are not runtime imports and are skipped.
"""

import ast
import pathlib
import re

import pytest

APP = pathlib.Path(__file__).resolve().parents[2]
SHARED_LOCK = APP / "shared" / "requirements.lock"
CONTEXTS = sorted(p.parent.parent.name for p in APP.glob("*/libraries/requirements.lock"))


def _pinned_stub_modules(lockfile: pathlib.Path) -> set[str]:
    names = re.findall(r"^(mypy-boto3-[a-z0-9-]+)==", lockfile.read_text(), flags=re.MULTILINE)
    return {name.replace("-", "_") for name in names}


def _is_type_checking_guard(node: ast.If) -> bool:
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _runtime_stub_imports(path: pathlib.Path) -> set[str]:
    found: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_type_checking_guard(node):
            for child in node.orelse:
                visit(child)
            return
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            names = []
        for name in names:
            top = name.split(".")[0]
            if top.startswith("mypy_boto3_"):
                found.add(top)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(ast.parse(path.read_text(), filename=str(path)))
    return found


def _source_files(root: pathlib.Path):
    for path in root.rglob("*.py"):
        parts = set(path.relative_to(APP).parts)
        if parts & {"tests", "test_utils"} or path.name.startswith("test_") or path.name == "conftest.py":
            continue
        yield path


@pytest.mark.parametrize("context", CONTEXTS)
def test_every_runtime_stub_import_is_pinned_in_a_layer(context):
    available = _pinned_stub_modules(APP / context / "libraries" / "requirements.lock") | _pinned_stub_modules(
        SHARED_LOCK
    )
    missing = {}
    for root in (APP / context, APP / "shared"):
        for path in _source_files(root):
            for module in _runtime_stub_imports(path) - available:
                missing.setdefault(module, []).append(str(path.relative_to(APP)))
    assert not missing, (
        f"{context}: stub modules imported at runtime but not pinned in "
        f"app/{context}/libraries/requirements.lock or app/shared/requirements.lock: {missing}"
    )


def test_contexts_are_discovered():
    assert {"packaging", "publishing", "provisioning", "projects"} <= set(CONTEXTS)
