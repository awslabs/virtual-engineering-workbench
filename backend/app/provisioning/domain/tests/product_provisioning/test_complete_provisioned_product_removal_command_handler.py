from unittest import mock

import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import complete_removal
from app.provisioning.domain.commands.product_provisioning import complete_provisioned_product_removal_command
from app.provisioning.domain.events.product_provisioning import provisioned_product_removed
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@freeze_time("2023-12-06")
def test_complete_virtual_target_removal_should_update_attributes_and_publish(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
):
    # ARRANGE
    command = complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        status=product_status.ProductStatus.Deprovisioning,
    )

    # ACT
    complete_removal.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        logger=mock_logger,
    )

    # ASSERT

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_removed.ProvisionedProductRemoved(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedCompoundProductId=None,
            awsAccountId="001234567890",
            region="us-east-1",
            instanceId="i-01234567890abcdef",
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
            status=product_status.ProductStatus.Terminated,
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
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )


@pytest.mark.parametrize("virtual_target_status", [product_status.ProductStatus.Terminated])
def test_complete_virtual_target_removal_when_status_not_deprovisioning_should_ignore(
    virtual_target_status,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
):
    # ARRANGE
    command = complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        status=virtual_target_status,
    )

    # ACT
    complete_removal.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
