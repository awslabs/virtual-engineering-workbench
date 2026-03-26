from unittest import mock

from app.provisioning.domain.command_handlers.provisioned_product_configuration import complete
from app.provisioning.domain.commands.provisioned_product_configuration import (
    complete_provisioned_product_configuration_command,
)
from app.provisioning.domain.events.product_provisioning import product_launched
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


def test_complete_provisioned_product_ec2_type_configuration_updates_db_and_publishes_event(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_provisioned_products_qs,
    mock_instance_mgmt_service,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    test_pp: provisioned_product.ProvisionedProduct = get_provisioned_product()
    test_pp.status = product_status.ProductStatus.Running
    test_pp.lastUpdateDate = mock.ANY

    # ACT
    complete.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qry_srv=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        test_pp,
    )
    mock_message_bus.publish.assert_called_once_with(
        product_launched.ProductLaunched(
            projectId="proj-123",
            provisionedProductId="pp-123",
            owner="T0011AA",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            privateIP="192.168.1.1",
            instanceId="i-01234567890abcdef",
            awsAccountId="001234567890",
            region="us-east-1",
        )
    )


# Container tests


def test_complete_provisioned_product_configuration_container_updates_db_and_publishes_event(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_provisioned_products_qs,
    mock_instance_mgmt_service,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container
    )
    command = complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    test_pp: provisioned_product.ProvisionedProduct = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container
    )
    test_pp.status = product_status.ProductStatus.Running
    test_pp.lastUpdateDate = mock.ANY

    # ACT
    complete.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qry_srv=mock_provisioned_products_qs,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        test_pp,
    )
    mock_message_bus.publish.assert_called_once_with(
        product_launched.ProductLaunched(
            projectId="proj-123",
            provisionedProductId="pp-123",
            owner="T0011AA",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.Container,
            privateIP="192.168.1.1",
            service_id="serv123",
            awsAccountId="001234567890",
            region="us-east-1",
        )
    )
