"""Every provisioning API operation behind the AVP authorizer is a Cedar action.

The authorizer sends the operation name to Verified Permissions as the action, so an operation
missing from ProvisioningBCActions is denied for every caller.
"""

import pathlib

import pytest
import yaml

from infra.auth.provisioning_auth_schema import ProvisioningBCActions

SCHEMA = (
    pathlib.Path(__file__).parents[3]
    / "app/provisioning/entrypoints/api/schema/proserve-workbench-provisioning-api-schema.yaml"
)
METHODS = ("get", "put", "post", "delete", "patch")


def _avp_operation_ids():
    spec = yaml.safe_load(SCHEMA.read_text())
    return sorted(
        operation["operationId"]
        for path in spec["paths"].values()
        for method, operation in path.items()
        if method in METHODS
        and any(
            "AVP-Request-Authorizer" in requirement
            for requirement in operation.get("security", spec.get("security", []))
        )
    )


@pytest.mark.parametrize("operation_id", _avp_operation_ids())
def test_avp_operation_is_a_provisioning_action(operation_id):
    assert operation_id in ProvisioningBCActions.__members__
