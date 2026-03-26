from unittest import mock

import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import stop_for_update
from app.provisioning.domain.commands.product_provisioning import stop_provisioned_product_for_update_command
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_stop_for_upgrade_failed,
    provisioned_product_stop_for_upgrade_initiated,
    provisioned_product_stopped_for_upgrade,
)
from app.provisioning.domain.model import (
    connection_option,
    container_details,
    instance_details,
    product_status,
    provisioned_product,
)
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    product_version_id_value_object,
    provisioned_product_id_value_object,
)


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
def test_handle_when_status_not_updating_should_publish_failure(
    virtual_target_status,
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    get_provisioned_product,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT

    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=True,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
            provisionedProductId="pp-123"
        )
    )


@freeze_time("2023-12-07")
def test_handle_when_ec2_is_running_should_stop_the_instance(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_provisioned_product_repo,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
    )

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_initiated.ProvisionedProductStopForUpgradeInitiated(
            provisionedProductId="pp-123"
        )
    )
    mock_instance_mgmt_srv.stop_instance.assert_called_once()
    mock_instance_mgmt_srv.stop_instance.assert_called_once_with(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", instance_id="i-01234567890abcdef"
    )

    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            last_update_date="2023-12-07T00:00:00+00:00",
        ),
    )


@freeze_time("2023-12-07")
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_handle_should_grant_user_ip_access_if_enabled(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
    )

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_initiated.ProvisionedProductStopForUpgradeInitiated(
            provisionedProductId="pp-123"
        )
    )
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option=option,
                    ip_address="127.0.0.1/32",
                    port=rule.from_port,
                    to_port=rule.to_port,
                    protocol=rule.protocol.value,
                    user_sg_id="sg-12345",
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()


@freeze_time("2023-12-07")
def test_handle_when_ec2_stop_fails_should_publish_failure_event(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
    )
    mock_instance_mgmt_srv.stop_instance.side_effect = Exception("Test")

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
            provisionedProductId="pp-123"
        )
    )


@freeze_time("2023-12-07")
def test_handle_when_ec2_is_stopped_should_publish_stopped_event(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[],
        block_device_mappings=get_test_block_device_mappings(),
    )

    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
    )

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(provisionedProductId="pp-123")
    )


# Container product type tests
@freeze_time("2023-12-07")
def test_handle_when_container_is_stopped_should_publish_stopped_event(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[],
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )

    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="STOPPED")

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(provisionedProductId="pp-123")
    )


@freeze_time("2023-12-07")
def test_handle_when_container_is_running_should_publish_stopped_for_update_initiated_event(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[],
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )

    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="RUNNING")

    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_initiated.ProvisionedProductStopForUpgradeInitiated(
            provisionedProductId="pp-123"
        )
    )


@freeze_time("2023-12-07")
def test_handle_when_container_is_running_should_publish_stopped_for_update_failed_event(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    get_test_block_device_mappings,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str("vers-123"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating,
        sc_provisioned_product_id="sc-pp-123",
        new_provisioning_parameters=[],
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )

    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="RUNNING")
    mock_container_mgmt_srv.stop_container.side_effect = Exception("Test")
    # ACT
    stop_for_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
            provisionedProductId="pp-123"
        )
    )
