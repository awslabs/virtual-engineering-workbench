from unittest import mock

import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import fail_launch
from app.provisioning.domain.commands.product_provisioning import fail_product_launch_command
from app.provisioning.domain.events.product_provisioning import insufficient_capacity_reached, product_launch_failed
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object

TEST_INSUFFICIENT_INSTANCE_CAPACITY = "Server.InsufficientInstanceCapacity"
TEST_PRODUCT_PARAM_TYPE_SUBNET_ID = "AWS::EC2::Subnet::Id"
TEST_PRODUCT_PARAM_TYPE_AZ = "AWS::EC2::AvailabilityZone::Name"


@freeze_time("2023-12-06")
def test_fail_launch_virtual_target_should_update_status_and_publish(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    mock_products_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
        ],
    )
    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )


def test_fail_launch_virtual_target_if_already_failed_should_not_publish(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.ProvisioningError,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
        ],
    )

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (
        ("SubnetId", TEST_PRODUCT_PARAM_TYPE_SUBNET_ID, "/workbench/vpc/subnet-id"),
        ("AZName", TEST_PRODUCT_PARAM_TYPE_AZ, "/workbench/az/az-name"),
    ),
)
def test_fail_launch_virtual_target_publish_insufficient_capacity_reached(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = True

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        insufficient_capacity_reached.InsufficientCapacityReached(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productType="VIRTUAL_TARGET",
            productName="Pied Piper",
            owner="T0011AA",
            userIpAddress="127.0.0.1",
        )
    )
    mock_unit_of_work.commit.assert_called_once()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (("SubnetId", "InvalidSubnetParamType", "/workbench/vpc/subnet-id"),),
)
def test_fail_launch_virtual_target_do_not_publish_insufficient_capacity_reached_id_parameter_type_invalid(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = True

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (
        ("SubnetId", TEST_PRODUCT_PARAM_TYPE_SUBNET_ID, "/workbench/vpc/subnet-id"),
        ("AZName", TEST_PRODUCT_PARAM_TYPE_AZ, "/workbench/az/az-name"),
    ),
)
def test_fail_launch_virtual_target_do_not_publish_insufficient_capacity_reached_if_instance_type_parameter_missing(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            # No Instance type parameter
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = False

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.assert_called_once()
    mock_unit_of_work.commit.assert_called_once()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (
        ("SubnetId", TEST_PRODUCT_PARAM_TYPE_SUBNET_ID, "/workbench/vpc/subnet-id"),
        ("AZName", TEST_PRODUCT_PARAM_TYPE_AZ, "/workbench/az/az-name"),
    ),
)
def test_fail_launch_single_az_deployment_should_fail_immediately_without_retry(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
        deployment_option="SINGLE_AZ",
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = True

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    # Should publish ProductLaunchFailed, not InsufficientCapacityReached
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedCompoundProductId=None,
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (
        ("SubnetId", TEST_PRODUCT_PARAM_TYPE_SUBNET_ID, "/workbench/vpc/subnet-id"),
        ("AZName", TEST_PRODUCT_PARAM_TYPE_AZ, "/workbench/az/az-name"),
    ),
)
def test_fail_launch_multi_az_deployment_should_retry_with_insufficient_capacity_event(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
        deployment_option="MULTI_AZ",
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = True

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    # Should publish InsufficientCapacityReached for retry logic
    mock_message_bus.publish.assert_called_once_with(
        insufficient_capacity_reached.InsufficientCapacityReached(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productType="VIRTUAL_TARGET",
            productName="Pied Piper",
            owner="T0011AA",
            userIpAddress="127.0.0.1",
        )
    )
    mock_unit_of_work.commit.assert_called_once()


@pytest.mark.parametrize(
    "parameter_key,parameter_type,parameter_value",
    (
        ("SubnetId", TEST_PRODUCT_PARAM_TYPE_SUBNET_ID, "/workbench/vpc/subnet-id"),
        ("AZName", TEST_PRODUCT_PARAM_TYPE_AZ, "/workbench/az/az-name"),
    ),
)
def test_fail_launch_none_deployment_option_should_retry_with_insufficient_capacity_event(
    parameter_key,
    parameter_type,
    parameter_value,
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_products_srv,
):
    # ARRANGE
    command = fail_product_launch_command.FailProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Provisioning,
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="c8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(
                key=parameter_key, value=parameter_value, isTechnicalParameter=True, parameterType=parameter_type
            ),
        ],
        user_ip_address="127.0.0.1",
        deployment_option=None,  # None should default to MULTI_AZ behavior
    )
    mock_products_srv.has_provisioned_product_insufficient_capacity_error.return_value = True

    # ACT
    fail_launch.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    # Should publish InsufficientCapacityReached for retry logic (backward compatibility)
    mock_message_bus.publish.assert_called_once_with(
        insufficient_capacity_reached.InsufficientCapacityReached(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productType="VIRTUAL_TARGET",
            productName="Pied Piper",
            owner="T0011AA",
            userIpAddress="127.0.0.1",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
