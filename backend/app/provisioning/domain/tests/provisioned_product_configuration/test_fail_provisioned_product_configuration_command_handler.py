from unittest import mock

from app.provisioning.domain.command_handlers.provisioned_product_configuration import fail
from app.provisioning.domain.commands.provisioned_product_configuration import (
    fail_provisioned_product_configuration_command,
)
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.value_objects import failure_reason_value_object, provisioned_product_id_value_object


def test_fail_provisioned_product_configuration_updates_product_state(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
):
    # ARRANGE
    command = fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        reason=failure_reason_value_object.from_str("Test"),
    )
    test_pp: provisioned_product.ProvisionedProduct = get_provisioned_product()
    test_pp.status = product_status.ProductStatus.ConfigurationFailed
    test_pp.statusReason = "Test"
    test_pp.lastUpdateDate = mock.ANY

    # ACT
    fail.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qry_srv=mock_provisioned_products_qs,
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
