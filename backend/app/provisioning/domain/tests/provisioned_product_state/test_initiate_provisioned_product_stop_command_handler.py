import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import initiate_stop
from app.provisioning.domain.commands.provisioned_product_state import initiate_provisioned_product_stop_command
from app.provisioning.domain.events.provisioned_product_state import provisioned_product_stop_initiated
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)

PROVISIONING_S2S_API_USER = "PROVISIONING_S2S_API_USER"


@freeze_time("2023-12-06")
def test_initiate_virtual_target_stop_should_initiate_virtual_target_stop(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        project_id=project_id_value_object.from_str("proj-123"),
    )
    # ACT
    initiate_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
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
            lastUpdatedBy="T0011AA",
        ),
    )


def test_initiate_virtual_target_stop_with_wrong_project_id_should_raise(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        project_id=project_id_value_object.from_str("wrong-project-id"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        initiate_stop.handle(
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
    command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_id=user_id_value_object.from_str("wrong-user-id"),
        project_id=project_id_value_object.from_str("proj-123"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        initiate_stop.handle(
            command=command,
            publisher=mock_publisher,
            virtual_targets_qs=mock_virtual_targets_qs,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("User is not allowed to modify the requested provisioned product.")
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    mock_virtual_target_repo.update_entity.assert_not_called()


@freeze_time("2023-12-06")
def test_initiate_stop_when_svc_acct_should_stop(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str(PROVISIONING_S2S_API_USER, user_id_value_object.UserIdType.Service),
    )
    # ACT
    initiate_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
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
            lastUpdatedBy=PROVISIONING_S2S_API_USER,
        ),
    )


def test_initiate_stop_when_svc_acct_should_validate_project(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
):
    # ARRANGE
    command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("wrong-project-id"),
        user_id=user_id_value_object.from_str(PROVISIONING_S2S_API_USER, user_id_value_object.UserIdType.Service),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        initiate_stop.handle(
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
