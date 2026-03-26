from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import remove_by_admin
from app.provisioning.domain.commands.product_provisioning import remove_provisioned_products_command
from app.provisioning.domain.events.product_provisioning import provisioned_product_removal_started
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
    user_role_value_object,
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
    command = remove_provisioned_products_command.RemoveProvisionedProductsCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011BB"),
        user_roles=[user_role_value_object.from_str("PROGRAM_OWNER")],
    )

    mock_provisioned_products_qs.get_by_id.side_effect = lambda provisioned_product_id: get_provisioned_product(
        status=product_status.ProductStatus.Running, provisioned_product_id=provisioned_product_id
    )

    # ACT
    remove_by_admin.handle(
        command=command,
        publisher=mock_publisher,
        logger=mock_logger,
        virtual_targets_qs=mock_provisioned_products_qs,
    )

    # ASSERT
    message_bus_calls = [
        mock.call(provisioned_product_removal_started.ProvisionedProductRemovalStarted(provisionedProductId="pp-123")),
        mock.call(provisioned_product_removal_started.ProvisionedProductRemovalStarted(provisionedProductId="pp-321")),
    ]
    mock_message_bus.publish.assert_has_calls(calls=message_bus_calls, any_order=True)

    mock_unit_of_work.commit.assert_has_calls(calls=[mock.call() for i in range(2)])

    update_entity_calls = [
        mock.call(
            provisioned_product.ProvisionedProductPrimaryKey(
                projectId="proj-123",
                provisionedProductId=provisioned_product_id,
            ),
            provisioned_product.ProvisionedProduct.construct(
                projectId="proj-123",
                provisionedProductId=provisioned_product_id,
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
                lastUpdatedBy="T0011BB",
            ),
        )
        for provisioned_product_id in ["pp-123", "pp-321"]
    ]

    mock_provisioned_product_repo.update_entity.assert_has_calls(calls=update_entity_calls, any_order=True)


def test_remove_virtual_target_when_user_unauthorized_should_raise(
    mock_logger,
    mock_publisher,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_provisioned_products_qs,
    get_provisioned_product,
):
    # ARRANGE
    command = remove_provisioned_products_command.RemoveProvisionedProductsCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_roles=[user_role_value_object.from_str("PLATFORM_USER")],
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        remove_by_admin.handle(
            command=command,
            publisher=mock_publisher,
            logger=mock_logger,
            virtual_targets_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    assertpy.assert_that(str(e.value)).is_equal_to("User is not allowed to modify the requested provisioned products.")


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
    command = remove_provisioned_products_command.RemoveProvisionedProductsCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_roles=[user_role_value_object.from_str("PLATFORM_USER")],
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT
    with pytest.raises(domain_exception.DomainException):
        remove_by_admin.handle(
            command=command,
            publisher=mock_publisher,
            logger=mock_logger,
            virtual_targets_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
