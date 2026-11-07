"""Every API operation behind the AVP authorizer is a Cedar action of its bounded context.

The authorizer sends the operation name to Verified Permissions as the action, so an operation
missing from the bounded context's actions is denied for every caller.
"""

import ast
import pathlib

import pytest
import yaml

APP_DIR = pathlib.Path(__file__).parents[1]
AUTH_DIR = APP_DIR.parent / "infra" / "auth"


def _action_names(bounded_context: str) -> frozenset[str]:
    """Read Cedar action enum members without importing CDK, which requires Node in CI."""
    module = ast.parse((AUTH_DIR / f"{bounded_context}_auth_schema.py").read_text())
    actions_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name.endswith("BCActions")
    )
    return frozenset(
        target.id
        for node in actions_class.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    )


BC_ACTIONS: dict[str, frozenset[str]] = {
    bounded_context: _action_names(bounded_context)
    for bounded_context in ("packaging", "projects", "provisioning", "publishing")
}
METHODS = ("get", "put", "post", "delete", "patch")


def _avp_operations():
    for bounded_context in BC_ACTIONS:
        for schema in sorted(APP_DIR.glob(f"{bounded_context}/entrypoints/*/schema/*-api-schema.yaml")):
            spec = yaml.safe_load(schema.read_text())
            for path in spec["paths"].values():
                for method, operation in path.items():
                    if method in METHODS and any(
                        "AVP-Request-Authorizer" in requirement
                        for requirement in operation.get("security", spec.get("security", []))
                    ):
                        yield pytest.param(
                            bounded_context, operation["operationId"], id=f"{schema.name}:{operation['operationId']}"
                        )


@pytest.mark.parametrize("bounded_context,operation_id", _avp_operations())
def test_avp_operation_is_a_bounded_context_action(bounded_context, operation_id):
    assert operation_id in BC_ACTIONS[bounded_context]
