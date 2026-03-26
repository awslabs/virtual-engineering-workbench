from unittest import mock

import assertpy
import pytest

from app.projects.domain.command_handlers.project_accounts import setup_static_resources_command_handler
from app.projects.domain.commands.project_accounts import setup_static_resources_command
from app.projects.domain.ports import iac_service
from app.projects.domain.value_objects import aws_account_id_value_object, region_value_object, variables_value_object


@pytest.fixture()
def command_mock():
    return setup_static_resources_command.SetupStaticResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        region=region_value_object.from_str("us-east-1"),
    )


@pytest.fixture()
def iac_service_mock():
    mock_srv = mock.create_autospec(spec=iac_service.IACService)
    mock_srv.deploy_iac.return_value = None
    return mock_srv


@pytest.mark.parametrize("variables", (None, {"key": "value"}))
def test_setup_static_resources_command_handler(
    command_mock, iac_service_mock, variables, mocked_ram_srv, mocked_ram_srv_tag
):
    # ARRANGE
    if variables:
        command_mock.variables = variables_value_object.from_dict(variables)

    # ACT
    setup_static_resources_command_handler.handle(
        cmd=command_mock, iac_srv=iac_service_mock, ram_srv=mocked_ram_srv, ram_resource_tag=mocked_ram_srv_tag
    )

    # ASSERT
    args = {"aws_account_id": command_mock.aws_account_id.value, "region": command_mock.region.value}
    if command_mock.variables:
        args["variables"] = command_mock.variables.value

    iac_service_mock.deploy_iac.assert_called_once_with(**args)


def test_setup_static_resources_command_handler_shares_ram_resources_in_the_region(
    command_mock, iac_service_mock, mocked_ram_srv, mocked_ram_srv_tag
):
    # ARRANGE
    mocked_ram_srv.get_resource_shares.return_value = ["ram-arn"]

    # ACT
    setup_static_resources_command_handler.handle(
        cmd=command_mock, iac_srv=iac_service_mock, ram_srv=mocked_ram_srv, ram_resource_tag=mocked_ram_srv_tag
    )

    # ASSERT
    tag_name, boto_cfg = mocked_ram_srv.get_resource_shares.call_args.kwargs.values()
    assertpy.assert_that(tag_name).is_equal_to(mocked_ram_srv_tag)
    assertpy.assert_that(boto_cfg.aws_region).is_equal_to(command_mock.region.value)
    assertpy.assert_that(boto_cfg.aws_account_id).is_none()

    mocked_ram_srv.associate_resource_share.assert_called_once()
    resource_share_arn, principals, boto_cfg_assoc = mocked_ram_srv.associate_resource_share.call_args.kwargs.values()
    assertpy.assert_that(resource_share_arn).is_equal_to("ram-arn")
    assertpy.assert_that(principals).is_equal_to([command_mock.aws_account_id.value])
    assertpy.assert_that(boto_cfg_assoc.aws_region).is_equal_to(command_mock.region.value)
    assertpy.assert_that(boto_cfg_assoc.aws_account_id).is_none()
