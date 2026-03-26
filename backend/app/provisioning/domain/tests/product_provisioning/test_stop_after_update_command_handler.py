import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import stop_after_update
from app.provisioning.domain.commands.product_provisioning import stop_provisioned_product_after_update_complete_command
from app.provisioning.domain.events.provisioned_product_state import provisioned_product_stop_initiated
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object

AUTO_STOP_AFTER_UPDATE_PROCESS_NAME = "AUTO_STOP_AFTER_UPDATE_PROCESS_NAME"


@pytest.fixture()
def mock_command():
    command = stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )
    return command


@freeze_time("2023-12-06")
def test_pp_stops_after_update(
    mock_command,
    mock_provisioned_product_repo,
    mock_unit_of_work,
    mock_message_bus,
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    get_provisioned_product,
):
    # ARRANGE
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        status=product_status.ProductStatus.Updating,
    )
    # ACT
    stop_after_update.handle(
        command=mock_command,
        logger=mock_logger,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
    )
    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-123")
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
            lastUpdatedBy=AUTO_STOP_AFTER_UPDATE_PROCESS_NAME,
        ),
    )
