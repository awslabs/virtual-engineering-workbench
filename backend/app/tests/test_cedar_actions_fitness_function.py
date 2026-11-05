"""Every API operation behind the AVP authorizer is a Cedar action of its bounded context.

The authorizer sends the operation name to Verified Permissions as the action, so an operation
missing from the bounded context's actions is denied for every caller.
"""

import enum
import pathlib

import pytest
import yaml

from infra.auth.packaging_auth_schema import PackagingBCActions
from infra.auth.projects_auth_schema import ProjectsBCActions
from infra.auth.provisioning_auth_schema import ProvisioningBCActions
from infra.auth.publishing_auth_schema import PublishingBCActions

APP_DIR = pathlib.Path(__file__).parents[1]
BC_ACTIONS: dict[str, type[enum.StrEnum]] = {
    "packaging": PackagingBCActions,
    "projects": ProjectsBCActions,
    "provisioning": ProvisioningBCActions,
    "publishing": PublishingBCActions,
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
    assert operation_id in BC_ACTIONS[bounded_context].__members__
