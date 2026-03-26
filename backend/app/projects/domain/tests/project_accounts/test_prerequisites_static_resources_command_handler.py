from unittest import mock

import pytest

from app.projects.domain.command_handlers.project_accounts import setup_prerequisites_resources_command_handler
from app.projects.domain.commands.project_accounts import setup_prerequisites_resources_command
from app.projects.domain.ports import iac_service
from app.projects.domain.value_objects import aws_account_id_value_object, region_value_object, variables_value_object

PREREQUISITES = {"prerequisites": "true"}


@pytest.fixture()
def command_mock():
    return setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        region=region_value_object.from_str("us-east-1"),
    )


@pytest.fixture()
def iac_service_mock():
    mock_srv = mock.create_autospec(spec=iac_service.IACService)
    mock_srv.deploy_iac.return_value = None
    return mock_srv


@pytest.mark.parametrize("variables", (None, {"key": "value"}))
def test_setup_static_resources_command_handler(command_mock, iac_service_mock, variables):
    # ARRANGE
    if variables:
        command_mock.variables = variables_value_object.from_dict(variables)

    # ACT
    setup_prerequisites_resources_command_handler.handle(cmd=command_mock, iac_srv=iac_service_mock)

    # ASSERT
    args = {
        "aws_account_id": command_mock.aws_account_id.value,
        "region": command_mock.region.value,
        "variables": PREREQUISITES,
    }
    if command_mock.variables:
        args["variables"] = {**command_mock.variables.value, **PREREQUISITES}

    iac_service_mock.deploy_iac.assert_called_once_with(**args)
