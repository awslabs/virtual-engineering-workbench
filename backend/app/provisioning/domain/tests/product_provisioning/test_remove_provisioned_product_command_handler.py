from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import remove
from app.provisioning.domain.commands.product_provisioning import remove_provisioned_product_command
from app.provisioning.domain.events.product_provisioning import provisioned_product_removal_started
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)


@freeze_time("2023-12-05")
def test_remove_virtual_target_sets_deprovisioning_status_and_publishes(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
):
    # ARRANGE
    command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running
    )

    # ACT
    remove.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_removal_started.ProvisionedProductRemovalStarted(provisionedProductId="pp-123")
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
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )


def test_remove_virtual_target_when_user_id_mismatch_should_raise(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
):
    # ARRANGE
    command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011BB"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        remove.handle(
            command=command,
            publisher=mock_publisher,
            logger=mock_logger,
            virtual_targets_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    assertpy.assert_that(str(e.value)).is_equal_to("User is not allowed to modify the requested provisioned product.")


@pytest.mark.parametrize(
    "virtual_target_status",
    [
        product_status.ProductStatus.Deprovisioning,
        product_status.ProductStatus.Provisioning,
        product_status.ProductStatus.Terminated,
    ],
)
def test_remove_virtual_target_when_wrong_status_should_raise(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
    virtual_target_status,
):
    # ARRANGE
    command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT
    with pytest.raises(domain_exception.DomainException):
        remove.handle(
            command=command,
            publisher=mock_publisher,
            logger=mock_logger,
            virtual_targets_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-05")
def test_remove_when_service_account_should_not_validate_user(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
):
    # ARRANGE
    command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("S2S_API_USER", user_id_value_object.UserIdType.Service),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running
    )

    # ACT
    remove.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_removal_started.ProvisionedProductRemovalStarted(provisionedProductId="pp-123")
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
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="S2S_API_USER",
        ),
    )
