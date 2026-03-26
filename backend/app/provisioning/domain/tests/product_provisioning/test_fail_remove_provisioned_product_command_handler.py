from unittest import mock

from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import fail_removal
from app.provisioning.domain.commands.product_provisioning import fail_provisioned_product_removal_command
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_removal_failed,
    provisioned_product_removal_retried,
)
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@freeze_time("2023-12-06")
def test_fail_remove_virtual_target_should_update_status_and_publish(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    mock_products_srv,
):
    # ARRANGE
    command = fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )
    # ACT
    fail_removal.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_removal_failed.ProvisionedProductRemovalFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedCompoundProductId=None,
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
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )


def test_fail_remove_virtual_target_if_already_failed_should_not_publish(
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
    command = fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.ProvisioningError
    )

    # ACT
    fail_removal.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-06")
def test_fail_remove_virtual_target_should_retry_deprovisioning_if_removal_signal_is_missing(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    mock_products_srv,
):
    # ARRANGE
    command = fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )
    mock_products_srv.has_provisioned_product_missing_removal_signal_error.return_value = True
    # ACT
    fail_removal.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_removal_retried.ProvisionedProductRemovalRetried(provisionedProductId="pp-123")
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
            status=product_status.ProductStatus.Deprovisioning,
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
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )
