from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import fail_update
from app.provisioning.domain.commands.product_provisioning import fail_provisioned_product_update
from app.provisioning.domain.events.product_provisioning import provisioned_product_upgrade_failed
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    block_device_mappings,
    product_status,
    provisioned_product,
    provisioned_product_output,
)
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@pytest.fixture()
def mock_versions_query_service(get_test_version):
    v = get_test_version()
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [v]
    qs_mock.get_by_provisioning_artifact_id.return_value = v
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
    mock_provisioned_product_repo,
    get_provisioned_product,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        fail_update.handle(
            command=command,
            publisher=mock_publisher,
            products_srv=mock_products_srv,
            provisioned_products_qs=mock_provisioned_products_qs,
            instance_mgmt_srv=mock_instance_mgmt_srv,
            container_mgmt_srv=mock_container_mgmt_srv,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Provisioned product pp-123 must be in UPDATING state (current state: {virtual_target_status})"
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-07")
def test_handle_should_publish_and_refresh_params(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
    )

    # ACT
    fail_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()

    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.outputs).contains_only(
        *[
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
        ]
    )

    assertpy.assert_that(stored_entity.instanceId).is_equal_to("i-1234567890")
    assertpy.assert_that(stored_entity.privateIp).is_equal_to("192.168.1.1")
    assertpy.assert_that(stored_entity.sshKeyPath).is_equal_to("/ec2/keypair/i-123")
    assertpy.assert_that(stored_entity.status).is_equal_to(product_status.ProductStatus.Stopped)


@freeze_time("2023-12-07")
def test_handle_should_set_to_provisioning_error_if_fails_to_fetch_status(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_instance_mgmt_srv.get_instance_details.side_effect = Exception("Error")

    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
    )

    # ACT
    fail_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()

    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.status).is_equal_to(product_status.ProductStatus.ProvisioningError)


@freeze_time("2023-12-07")
def test_handle_should_attach_second_ebs_volume_if_it_exists(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    # Added
    mock_parameter_srv,
    get_test_block_device_mappings,
    default_subnet_selector,
    mock_container_mgmt_srv,
    #
):
    # ARRANGE
    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        block_device_mappings=get_test_block_device_mappings(),
    )

    # ACT
    fail_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.attach_instance_volume.assert_called_once()
    mock_instance_mgmt_srv.attach_instance_volume.assert_called_once_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id="i-1234567890",
        volume_id="vol-0987654321",
        device_name="/dev/sdb",
    )


@freeze_time("2023-12-07")
def test_handle_should_not_attach_second_ebs_volume_if_it_is_not_exist(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    # Added
    mock_parameter_srv,
    get_test_block_device_mappings,
    default_subnet_selector,
    mock_container_mgmt_srv,
    #
):
    # ARRANGE
    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
    )
    mock_instance_mgmt_srv.get_block_device_mappings.return_value = block_device_mappings.BlockDeviceMappings(
        rootDeviceName="/dev/sda1",
        mappings=[],
    )

    # ACT
    fail_update.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.attach_instance_volume.assert_not_called()
