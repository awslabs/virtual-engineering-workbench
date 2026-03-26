import ipaddress
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.command_handlers.product_provisioning import update_product
from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_update_started,
    provisioned_product_upgrade_failed,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    network_interface,
    network_route_table,
    network_subnet,
    product_status,
    provisioned_product,
    provisioned_product_output,
    provisioning_parameter,
)
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@pytest.fixture()
def mock_versions_query_service(get_test_version):
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [
        get_test_version(
            parameters=[
                version.VersionParameter(
                    parameterKey="SomeParam",
                    defaultValue="some-default",
                    parameterType="String",
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ]
        )
    ]
    return qs_mock


@pytest.mark.parametrize(
    "virtual_target_status", [s for s in product_status.ProductStatus if s != product_status.ProductStatus.Updating]
)
def test_handle_when_status_not_updating_should_raise(
    virtual_target_status,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    get_provisioned_product,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    mock_versions_query_service,
    default_subnet_selector,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_product.handle(
            command=command,
            publisher=mock_publisher,
            products_srv=mock_products_srv,
            provisioned_products_qs=mock_provisioned_products_qs,
            instance_mgmt_srv=mock_instance_mgmt_srv,
            container_mgmt_srv=mock_container_mgmt_srv,
            logger=mock_logger,
            versions_qs=mock_versions_query_service,
            parameter_srv=mock_parameter_srv,
            spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
            subnet_selector=default_subnet_selector,
            uow=mock_unit_of_work,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Provisioned product pp-123 must be in UPDATING state (current state: {virtual_target_status})"
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-07")
def test_handle_should_update_provisioned_product(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_versions_query_service,
    default_subnet_selector,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
        ],
    )

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="UserSecurityGroupId", value="sg-12345", isTechnicalParameter=True
            ),
            provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
        ],
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_update_started.ProvisionedProductUpdateStarted(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="UserSecurityGroupId", value="sg-12345", isTechnicalParameter=True
                ),
                provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )
    mock_instance_mgmt_srv.create_user_security_group.assert_not_called()


@freeze_time("2023-12-07")
@pytest.mark.parametrize(
    "param_name,param_type,param_value",
    [
        ("SubnetId", "AWS::EC2::Subnet::Id", "s-prv-1"),
        ("SubnetsIds", "List<AWS::EC2::Subnet::Id>", "s-prv-1,s-prv-2"),
        ("AZName", "AWS::EC2::AvailabilityZone::Name", "az-1"),
    ],
)
def test_handle_when_new_params_contain_subnet_param_should_populate(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    param_name,
    param_type,
    param_value,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_subnet,
    mock_private_route_table,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
    )

    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=80, availability_zone="az-2"),
    ]

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, value=param_value, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key=param_name, value=param_value, isTechnicalParameter=True, parameterType=param_type
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_new_params_contain_subnet_id_should_take_from_provisioning_params(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
    )

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
            ],
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_new_params_contain_subnets_ids_should_take_from_provisioning_params(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds", isTechnicalParameter=True, parameterType="List<AWS::EC2::Subnet::Id>"
            ),
        ],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds",
                value="s-prv-old-1,s-prv-old-2",
                isTechnicalParameter=True,
                parameterType="List<AWS::EC2::Subnet::Id>",
            ),
        ],
    )

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds",
                value="s-prv-old-1,s-prv-old-2",
                isTechnicalParameter=True,
                parameterType="List<AWS::EC2::Subnet::Id>",
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetsIds",
                    value="s-prv-old-1,s-prv-old-2",
                    isTechnicalParameter=True,
                    parameterType="List<AWS::EC2::Subnet::Id>",
                ),
            ],
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetsIds",
                    value="s-prv-old-1,s-prv-old-2",
                    isTechnicalParameter=True,
                    parameterType="List<AWS::EC2::Subnet::Id>",
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_new_params_contain_az_should_take_az_of_the_subnet_from_provisioning_params(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="AZName", isTechnicalParameter=True, parameterType="AWS::EC2::AvailabilityZone::Name"
            ),
        ],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
    )

    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        network_subnet.NetworkSubnet(
            subnet_id="s-prv-old",
            available_ip_address_count=100,
            availability_zone="az-2",
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        ),
        network_subnet.NetworkSubnet(
            subnet_id="s-prv-other",
            available_ip_address_count=120,
            availability_zone="az-1",
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        ),
    ]

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="AZName", value="az-2", isTechnicalParameter=True, parameterType="AWS::EC2::AvailabilityZone::Name"
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
            ],
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="AZName",
                    value="az-2",
                    isTechnicalParameter=True,
                    parameterType="AWS::EC2::AvailabilityZone::Name",
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_update_fails_should_publish_failure_event(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_versions_query_service,
    default_subnet_selector,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
    )
    mock_products_srv.update_product.side_effect = Exception("Test")

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Stopped,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            status_reason="Test",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="instance-id", outputValue="i-1234567890", description="description"
                ),
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="privateIp", outputValue="192.168.1.1", description="description"
                ),
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="SSHKeyPair",
                    outputValue="/ec2/keypair/i-123",
                    description="SSM Parameter containing the ssh key generated",
                ),
            ],
            instance_id="i-1234567890",
            private_ip="192.168.1.1",
            ssh_key_path="/ec2/keypair/i-123",
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_has_ebs_volume_should_detach(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_versions_query_service,
    default_subnet_selector,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[],
        block_device_mappings=get_test_block_device_mappings(),
    )

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_instance_mgmt_srv.detach_instance_volume.assert_called_once()
    mock_instance_mgmt_srv.detach_instance_volume.assert_called_once_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id="i-01234567890abcdef",
        volume_id="vol-0987654321",
    )

    mock_products_srv.update_product.assert_called_once()

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_update_started.ProvisionedProductUpdateStarted(provisionedProductId="pp-123")
    )


@freeze_time("2023-12-07")
def test_handle_when_new_params_contain_ip_should_take_ip_from_the_subnet_of_provisioning_params(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                isTechnicalParameter=True,
            ),
        ],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                value="192.168.1.254",
                isTechnicalParameter=True,
            ),
        ],
    )

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                value="192.168.1.254",
                isTechnicalParameter=True,
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="VEWAllocatedIPAddress", value="192.168.1.254", isTechnicalParameter=True
                ),
            ],
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="VEWAllocatedIPAddress", value="192.168.1.254", isTechnicalParameter=True
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
        ),
    )


@freeze_time("2023-12-07")
def test_handle_when_new_params_contain_ip_but_not_in_prov_params_should_allocate_ip(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
    mock_unit_of_work,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                isTechnicalParameter=True,
            ),
        ],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
    )

    mock_instance_mgmt_srv.describe_subnet.return_value = network_subnet.NetworkSubnet(
        AvailabilityZone="az-1",
        CidrBlock="192.168.1.0/24",
        SubnetId="s-prv",
        VpcId="XXXXXXX",
        Tags=[],
        AvailableIpAddressCount=100,
    )
    mock_instance_mgmt_srv.describe_subnet_interfaces.return_value = [
        network_interface.NetworkInterface(
            NetworkInterfaceId="XXXXXXX",
            PrivateIpAddresses=[network_interface.PrivateIpAddress(PrivateIpAddress=str(ip))],
        )
        for ip in ipaddress.IPv4Network("192.168.1.0/24").hosts()
        if not str(ip).endswith((".1", ".2", ".3", ".254"))
    ]

    # ACT
    update_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.update_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_provisioned_product_id="sc-pp-123",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-vers-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                value="192.168.1.254",
                isTechnicalParameter=True,
            ),
        ],
        region="us-east-1",
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            sc_provisioned_product_id="sc-pp-123",
            last_update_date="2023-12-07T00:00:00+00:00",
            provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
            ],
            new_provisioning_parameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv-old", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="VEWAllocatedIPAddress", value="192.168.1.254", isTechnicalParameter=True
                ),
            ],
            block_device_mappings=get_test_block_device_mappings(),
            private_ip="192.168.1.254",
        ),
    )
