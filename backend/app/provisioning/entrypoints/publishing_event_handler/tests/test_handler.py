from app.provisioning.domain.commands.product_provisioning import (
    check_if_upgrade_available_command,
)
from app.provisioning.domain.read_models import component_version_detail, product
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_version_id_value_object,
    product_version_name_value_object,
    region_value_object,
    version_stage_value_object,
)

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]


def test_handler_product_availability_updated_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_availability_updated_event_payload,
    mock_update_product_read_model_event_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.publishing_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductAvailabilityUpdated",
        detail=product_availability_updated_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_product_read_model_event_handler.assert_called_once_with(
        product.Product(
            projectId="proj-12345",
            productId="prod-12345",
            productType=product.ProductType.Workbench,
            productName="mock-name",
            productDescription="mock description",
            technologyId="tech-12345",
            technologyName="Technology 1",
            availableStages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
            availableRegions=["us-east-1", "eu-west-1"],
            pausedStages=[],
            pausedRegions=[],
            lastUpdateDate="mock-time",
        )
    )


def test_product_version_published_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_published_payload,
    mock_check_upgrade_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.publishing_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(detail_type="ProductVersionPublished", detail=product_version_published_payload)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_check_upgrade_command_handler.assert_called_once_with(
        check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
            product_id=product_id_value_object.from_str("prod-123"),
            product_version_id=product_version_id_value_object.from_str("vers-123"),
            product_version_name=product_version_name_value_object.from_str("3.9.1-rc.3"),
            region=region_value_object.from_str("us-east-1"),
            stage=version_stage_value_object.from_str("dev"),
        )
    )


def test_update_recommended_version_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    recommended_version_set_payload,
    mock_update_recommended_version_read_model_event_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.publishing_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(detail_type="RecommendedVersionSet", detail=recommended_version_set_payload)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_recommended_version_read_model_event_handler.assert_called_once_with(
        project_id="proj-123",
        product_id="prod-123",
        new_recommended_version_id="vers-2",
    )
