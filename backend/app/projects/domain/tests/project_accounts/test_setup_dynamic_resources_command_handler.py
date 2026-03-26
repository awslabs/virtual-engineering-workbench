from unittest import mock

import assertpy
import pytest

from app.projects.domain.command_handlers.project_accounts import setup_dynamic_resources_command_handler
from app.projects.domain.commands.project_accounts import setup_dynamic_resources_command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import dynamic_parameter
from app.projects.domain.ports import dns_service, network_service
from app.projects.domain.value_objects import aws_account_id_value_object, region_value_object
from app.shared.adapters.boto import parameter_service_v2
from app.shared.domain.ports import secret_service


@pytest.fixture()
def command_mock():
    return setup_dynamic_resources_command.SetupDynamicResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        region=region_value_object.from_str("us-east-1"),
    )


@pytest.fixture()
def dns_service_mock():
    mock_srv = mock.create_autospec(spec=dns_service.DNSService)
    mock_srv.get_zone_id.return_value = "Z1ABCDEFGHIJK2"
    mock_srv.create_private_zone.return_value = "Z1ABCDEFGHIJK2"
    mock_srv.is_vpc_associated_with_zone.return_value = False
    return mock_srv


@pytest.fixture()
def network_service_mock():
    mock_srv = mock.create_autospec(spec=network_service.NetworkService)
    mock_srv.get_vpc_id_by_tag.return_value = "vpc-012345678901"
    mock_srv.get_vpcs_ids.return_value = ["vpc-012345678901", "vpc-123456789012"]
    mock_srv.get_subnets_by_tag.return_value = [
        {"SubnetId": "subnet-123", "CidrBlock": "172.31.1.0/24"},
        {"SubnetId": "subnet-456", "CidrBlock": "172.31.2.0/24"},
    ]
    return mock_srv


@pytest.fixture()
def parameter_service_mock():
    mock_srv = mock.create_autospec(spec=parameter_service_v2.ParameterService)
    mock_srv.create_string_parameter.return_value = None
    return mock_srv


@pytest.fixture()
def secrets_service_mock():
    mock_srv = mock.create_autospec(spec=secret_service.SecretsService)
    return mock_srv


def test_should_handle_setup_dynamic_resources_command(
    command_mock,
    dns_service_mock,
    network_service_mock,
    parameter_service_mock,
    secrets_service_mock,
):
    # ARRANGE
    cmd = command_mock
    dns_service_mock.get_zone_id.return_value = None
    secrets_ids_to_propagate = [
        "secret-1",
        "secret-2",
        "secret-3",
    ]
    secrets_names_and_descriptions = [
        ("secret-1", "description-1"),
        ("secret-2", "description-2"),
        ("secret-3", "description-3"),
    ]
    secret_srv = secrets_service_mock
    secret_srv.get_secrets_ids_by_path.side_effect = [["secret-1", "secret-2"], ["secret-3"]]
    secret_srv.describe_secret.side_effect = secrets_names_and_descriptions
    secrets_values = [
        "value-1",
        "value-2",
        "value-3",
    ]
    secret_srv.get_secret_value.side_effect = secrets_values
    parameter_service_mock.get_parameter_value.return_value = "vpc-012345678901"

    # ACT
    setup_dynamic_resources_command_handler.handle(
        cmd=cmd,
        dns_records={
            "records": [
                {
                    "name": "www",
                    "ttl": 300,
                    "type": "CNAME",
                    "value": {
                        "us-east-1": "www.test.com.",
                    },
                },
            ],
        },
        dns_srv=dns_service_mock,
        spoke_account_secrets_scope="/path",
        secrets_srv=secret_srv,
        network_srv=network_service_mock,
        parameter_srv=parameter_service_mock,
        parameters=[
            dynamic_parameter.DynamicParameter(
                name="/workbench/vpc/vpc-id",
                type=dynamic_parameter.DynamicParameterType.VPC_ID,
                tag="onboarding:enabled",
            ),
            dynamic_parameter.DynamicParameter(
                name="/workbench/vpc/backend-subnet-ids",
                type=dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_IDS,
                tag="subnet_type:backend",
            ),
            dynamic_parameter.DynamicParameter(
                name="/workbench/vpc/backend-subnet-cidrs",
                type=dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_CIDRS,
            ),
        ],
        zone_name="example.com",
    )

    # ASSERT
    dns_service_mock.get_zone_id.assert_called_once_with(
        dns_name="example.com",
        provider_options=mock.ANY,
    )
    dns_service_mock.create_private_zone.assert_called_once_with(
        comment="Private hosted zone for Virtual Engineering Workbench (VEW).",
        dns_name="example.com",
        provider_options=mock.ANY,
        vpc_id="vpc-012345678901",
        vpc_region=cmd.region.value,
    )
    for vpc_id in ["vpc-012345678901", "vpc-123456789012"]:
        dns_service_mock.associate_vpc_with_zone.assert_any_call(
            provider_options=mock.ANY,
            vpc_id=vpc_id,
            vpc_region=cmd.region.value,
            zone_id="Z1ABCDEFGHIJK2",
        )
    dns_service_mock.create_dns_record.assert_called_once_with(
        name="www.example.com",
        provider_options=mock.ANY,
        type="CNAME",
        ttl=300,
        value="www.test.com.",
        zone_id="Z1ABCDEFGHIJK2",
    )
    for index, secret_id in enumerate(secrets_ids_to_propagate):
        secret_srv.describe_secret.assert_any_call(secret_name=secret_id)
        secret_srv.get_secret_value.assert_any_call(secret_name=secret_id)
        secret_srv.upsert_secret.assert_any_call(
            secret_name=secrets_names_and_descriptions[index][0],
            secret_value=secrets_values[index],
            description=secrets_names_and_descriptions[index][1],
            provider_options=mock.ANY,
        )
    parameter_service_mock.create_string_parameter.assert_any_call(
        parameter_name="/workbench/vpc/backend-subnet-ids",
        parameter_value="subnet-123,subnet-456",
        is_overwrite=True,
        provider_options=mock.ANY,
    )
    parameter_service_mock.create_string_parameter.assert_any_call(
        parameter_name="/workbench/vpc/backend-subnet-cidrs",
        parameter_value="172.31.1.0/24,172.31.2.0/24",
        is_overwrite=True,
        provider_options=mock.ANY,
    )


def test_should_not_configure_dns_if_no_vpcs(
    command_mock,
    dns_service_mock,
    network_service_mock,
    parameter_service_mock,
    secrets_service_mock,
):
    # ARRANGE
    cmd = command_mock
    network_service_mock.get_vpcs_ids.return_value = []
    secrets_ids_to_propagate = [
        "secret-1",
        "secret-2",
        "secret-3",
    ]
    secrets_names_and_descriptions = [
        ("secret-1", "description-1"),
        ("secret-2", "description-2"),
        ("secret-3", "description-3"),
    ]
    secret_srv = secrets_service_mock
    secret_srv.describe_secret.side_effect = secrets_names_and_descriptions
    secrets_values = [
        "value-1",
        "value-2",
        "value-3",
    ]
    secret_srv.get_secret_value.side_effect = secrets_values

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        setup_dynamic_resources_command_handler.handle(
            cmd=cmd,
            dns_records={
                "records": [
                    {
                        "name": "www",
                        "ttl": 300,
                        "type": "CNAME",
                        "value": {
                            "us-east-1": "www.test.com.",
                        },
                    },
                ],
            },
            dns_srv=dns_service_mock,
            spoke_account_secrets_scope="/path",
            secrets_srv=secret_srv,
            network_srv=network_service_mock,
            parameter_srv=parameter_service_mock,
            parameters=[
                dynamic_parameter.DynamicParameter(
                    name="/workbench/vpc/vpc-id",
                    type=dynamic_parameter.DynamicParameterType.VPC_ID,
                    tag="onboarding:enabled",
                )
            ],
            zone_name="example.com",
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "No VPCs found in the account 123456789012 at region us-east-1"
    )
    dns_service_mock.get_zone_id.assert_not_called()
    dns_service_mock.create_private_zone.assert_not_called()
    dns_service_mock.associate_vpc_with_zone.assert_not_called()
    dns_service_mock.create_dns_record.assert_not_called()


def test_should_not_create_zone_if_already_exist(
    command_mock,
    dns_service_mock,
    network_service_mock,
    parameter_service_mock,
    secrets_service_mock,
):
    # ARRANGE
    cmd = command_mock
    secrets_ids_to_propagate = [
        "secret-1",
        "secret-2",
        "secret-3",
    ]
    secrets_names_and_descriptions = [
        ("secret-1", "description-1"),
        ("secret-2", "description-2"),
        ("secret-3", "description-3"),
    ]
    secret_srv = secrets_service_mock
    secret_srv.describe_secret.side_effect = secrets_names_and_descriptions
    secrets_values = [
        "value-1",
        "value-2",
        "value-3",
    ]
    secret_srv.get_secret_value.side_effect = secrets_values

    # ACT
    setup_dynamic_resources_command_handler.handle(
        cmd=cmd,
        dns_records={
            "records": [
                {
                    "name": "www",
                    "ttl": 300,
                    "type": "CNAME",
                    "value": {
                        "us-east-1": "www.test.com.",
                    },
                },
            ],
        },
        dns_srv=dns_service_mock,
        spoke_account_secrets_scope="/path",
        secrets_srv=secret_srv,
        network_srv=network_service_mock,
        parameter_srv=parameter_service_mock,
        parameters=[
            dynamic_parameter.DynamicParameter(
                name="/workbench/vpc/vpc-id",
                type=dynamic_parameter.DynamicParameterType.VPC_ID,
                tag="onboarding:enabled",
            )
        ],
        zone_name="example.com",
    )

    # ASSERT
    dns_service_mock.get_zone_id.assert_called_once_with(
        dns_name="example.com",
        provider_options=mock.ANY,
    )
    dns_service_mock.create_private_zone.assert_not_called()
    for vpc_id in ["vpc-012345678901", "vpc-123456789012"]:
        dns_service_mock.associate_vpc_with_zone.assert_any_call(
            provider_options=mock.ANY,
            vpc_id=vpc_id,
            vpc_region=cmd.region.value,
            zone_id="Z1ABCDEFGHIJK2",
        )
    dns_service_mock.create_dns_record.assert_called_once_with(
        name="www.example.com",
        provider_options=mock.ANY,
        type="CNAME",
        ttl=300,
        value="www.test.com.",
        zone_id="Z1ABCDEFGHIJK2",
    )


def test_should_not_associate_zone_if_already_associated(
    command_mock,
    dns_service_mock,
    network_service_mock,
    parameter_service_mock,
    secrets_service_mock,
):
    # ARRANGE
    cmd = command_mock
    dns_service_mock.is_vpc_associated_with_zone.return_value = True
    secrets_ids_to_propagate = [
        "secret-1",
        "secret-2",
        "secret-3",
    ]
    secrets_names_and_descriptions = [
        ("secret-1", "description-1"),
        ("secret-2", "description-2"),
        ("secret-3", "description-3"),
    ]
    secret_srv = secrets_service_mock
    secret_srv.describe_secret.side_effect = secrets_names_and_descriptions
    secrets_values = [
        "value-1",
        "value-2",
        "value-3",
    ]
    secret_srv.get_secret_value.side_effect = secrets_values

    # ACT
    setup_dynamic_resources_command_handler.handle(
        cmd=cmd,
        dns_records={
            "records": [
                {
                    "name": "www",
                    "ttl": 300,
                    "type": "CNAME",
                    "value": {
                        "us-east-1": "www.test.com.",
                    },
                },
            ],
        },
        dns_srv=dns_service_mock,
        spoke_account_secrets_scope="/path",
        secrets_srv=secret_srv,
        network_srv=network_service_mock,
        parameter_srv=parameter_service_mock,
        parameters=[
            dynamic_parameter.DynamicParameter(
                name="/workbench/vpc/vpc-id",
                type=dynamic_parameter.DynamicParameterType.VPC_ID,
                tag="onboarding:enabled",
            )
        ],
        zone_name="example.com",
    )

    # ASSERT
    dns_service_mock.get_zone_id.assert_called_once_with(
        dns_name="example.com",
        provider_options=mock.ANY,
    )
    dns_service_mock.create_private_zone.assert_not_called()
    dns_service_mock.associate_vpc_with_zone.assert_not_called()
    dns_service_mock.create_dns_record.assert_called_once_with(
        name="www.example.com",
        provider_options=mock.ANY,
        type="CNAME",
        ttl=300,
        value="www.test.com.",
        zone_id="Z1ABCDEFGHIJK2",
    )
