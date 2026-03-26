from unittest import mock

from app.provisioning.domain.command_handlers.provisioned_product_configuration import start
from app.provisioning.domain.commands.provisioned_product_configuration import (
    start_provisioned_product_configuration_command,
)
from app.provisioning.domain.events.provisioned_product_configuration import provisioned_product_configuration_started
from app.provisioning.domain.model import additional_configuration, product_status, provisioned_product
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


def test_start_provisioned_product_configuration_updates_db_runs_document_publishes_event(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_provisioned_products_qs,
    mock_system_command_service,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
):
    # ARRANGE
    command = start_provisioned_product_configuration_command.StartProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    test_pp: provisioned_product.ProvisionedProduct = get_provisioned_product()
    test_pp.status = product_status.ProductStatus.ConfigurationInProgress
    test_pp.lastUpdateDate = mock.ANY
    test_pp.additionalConfigurations[0].run_id = "doc-123"

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qry_srv=mock_provisioned_products_qs,
        system_command_srv=mock_system_command_service,
        logger=mock_logger,
    )

    # ASSERT
    mock_unit_of_work.commit.assert_called_once()
    mock_system_command_service.run_document.assert_called_once_with(
        aws_account_id="001234567890",
        region="us-east-1",
        user_id="T0011AA",
        provisioned_product_configuration_type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
        instance_id="i-01234567890abcdef",
        parameters=[
            additional_configuration.AdditionalConfigurationParameter(key="param-1", value="value-1"),
            additional_configuration.AdditionalConfigurationParameter(key="param-2", value="value-2"),
        ],
    )
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        test_pp,
    )
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_configuration_started.ProvisionedProductConfigurationStarted(provisionedProductId="pp-123")
    )
