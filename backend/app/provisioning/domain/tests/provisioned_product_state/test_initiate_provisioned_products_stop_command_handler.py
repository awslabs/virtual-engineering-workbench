from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import initiate_stop_by_admin
from app.provisioning.domain.commands.provisioned_product_state import initiate_provisioned_products_stop_command
from app.provisioning.domain.events.provisioned_product_state import provisioned_product_stop_initiated
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
    user_role_value_object,
)


@freeze_time("2023-12-06")
def test_initiate_virtual_targets_stop_should_initiate_virtual_targets_stop(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
):
    # ARRANGE
    command = initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        user_id=user_id_value_object.from_str("T0011BB"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_roles=[user_role_value_object.from_str("PROGRAM_OWNER")],
    )
    mock_virtual_targets_qs.get_by_id.side_effect = lambda provisioned_product_id: get_virtual_target(
        status=product_status.ProductStatus.Running, provisioned_product_id=provisioned_product_id
    )

    # ACT
    initiate_stop_by_admin.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        logger=mock_logger,
    )

    # ASSERT
    message_bus_calls = [
        mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-123")),
        mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-321")),
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
                provisionedProductName="my name",
                provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
                userId="T0011AA",
                userDomains=["domain"],
                status=product_status.ProductStatus.Stopping,
                productId="prod-123",
                productName="Pied Piper",
                productDescription="Compression",
                technologyId="tech-123",
                versionId="vers-123",
                versionName="v1.0.0",
                awsAccountId="001234567890",
                accountId="acc-123",
                instanceId="i-01234567890abcdef",
                stage=provisioned_product.ProvisionedProductStage.DEV,
                region="us-east-1",
                amiId="ami-123",
                scProductId="sc-prod-123",
                scProvisioningArtifactId="sc-pa-123",
                scProvisionedProductId=None,
                provisioningParameters=[
                    provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                    provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
                ],
                createDate="2023-12-05T00:00:00+00:00",
                lastUpdateDate="2023-12-06T00:00:00+00:00",
                createdBy="T0011AA",
                lastUpdatedBy="T0011BB",
            ),
        )
        for provisioned_product_id in ["pp-123", "pp-321"]
    ]
    mock_virtual_target_repo.update_entity.assert_has_calls(calls=update_entity_calls, any_order=True)


def test_initiate_virtual_target_stop_with_wrong_project_id_should_raise(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        user_id=user_id_value_object.from_str("T0011AA"),
        project_id=project_id_value_object.from_str("wrong-project-id"),
        user_roles=[user_role_value_object.from_str("PROGRAM_OWNER")],
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        initiate_stop_by_admin.handle(
            command=command,
            publisher=mock_publisher,
            virtual_targets_qs=mock_virtual_targets_qs,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Provided project ID is different from the provisioned product project ID"
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    mock_virtual_target_repo.update_entity.assert_not_called()


def test_initiate_virtual_target_stop_with_unauthorized_user_should_raise(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand(
        provisioned_product_ids=[
            provisioned_product_id_value_object.from_str("pp-123"),
            provisioned_product_id_value_object.from_str("pp-321"),
        ],
        user_id=user_id_value_object.from_str("T0011AA"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_roles=[user_role_value_object.from_str("PLATFORM_USER")],
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        initiate_stop_by_admin.handle(
            command=command,
            publisher=mock_publisher,
            virtual_targets_qs=mock_virtual_targets_qs,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("User is not allowed to modify the requested provisioned products.")
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    mock_virtual_target_repo.update_entity.assert_not_called()
