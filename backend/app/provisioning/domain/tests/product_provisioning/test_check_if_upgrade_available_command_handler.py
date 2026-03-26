from unittest import mock

import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import check_if_upgrade_available
from app.provisioning.domain.commands.product_provisioning import check_if_upgrade_available_command
from app.provisioning.domain.events.product_provisioning import provisioned_product_upgrade_available
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.ports import provisioned_products_query_service
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_version_id_value_object,
    product_version_name_value_object,
    region_value_object,
    version_stage_value_object,
)


@freeze_time("2023-12-05")
@pytest.mark.parametrize("new_version", ["1.2.3", "1.2.3-rc.2", "1.2.3-restored.1"])
def test_handle_when_current_version_is_different_should_mark_for_upgrade(
    get_provisioned_product, mock_publisher, mock_message_bus, mock_provisioned_product_repo, mock_logger, new_version
):
    # ARRANGE
    mocked_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    mocked_qs.get_all_provisioned_products_by_product_id.return_value = [
        get_provisioned_product(version_id="vers-123", version_name="1.0.0"),
        get_provisioned_product(version_id="vers-321", provisioned_product_id="pp-321", version_name="1.0.0"),
    ]

    command = check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
        product_id=product_id_value_object.from_str("p-123"),
        product_version_id=product_version_id_value_object.from_str("vers-456"),
        product_version_name=product_version_name_value_object.from_str(new_version),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
    )

    # ACT
    check_if_upgrade_available.handle(
        command=command, publisher=mock_publisher, logger=mock_logger, pp_qry_srv=mocked_qs
    )

    # ASSERT
    mocked_qs.get_all_provisioned_products_by_product_id.assert_called_once_with(
        product_id="p-123",
        region="us-east-1",
        stage="DEV",
    )
    mock_message_bus.publish.assert_any_call(
        provisioned_product_upgrade_available.ProvisionedProductUpgradeAvailable(provisionedProductId="pp-123")
    )
    mock_message_bus.publish.assert_any_call(
        provisioned_product_upgrade_available.ProvisionedProductUpgradeAvailable(provisionedProductId="pp-321")
    )
    mock_provisioned_product_repo.update_entity.assert_any_call(
        pk=provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        entity=get_provisioned_product(
            version_id="vers-123",
            new_version_id="vers-456",
            new_version_name=new_version,
            upgrade_available=True,
            version_name="1.0.0",
        ),
    )
    mock_provisioned_product_repo.update_entity.assert_any_call(
        pk=provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-321",
        ),
        entity=get_provisioned_product(
            version_id="vers-321",
            provisioned_product_id="pp-321",
            new_version_id="vers-456",
            new_version_name=new_version,
            upgrade_available=True,
            version_name="1.0.0",
        ),
    )


def test_handle_when_current_version_is_the_same_should_not_mark_for_upgrade(
    get_provisioned_product, mock_publisher, mock_message_bus, mock_provisioned_product_repo, mock_logger
):
    # ARRANGE
    mocked_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    mocked_qs.get_all_provisioned_products_by_product_id.return_value = [
        get_provisioned_product(version_id="vers-456", version_name="1.0.0"),
        get_provisioned_product(version_id="vers-456", provisioned_product_id="pp-321", version_name="1.0.0"),
    ]

    command = check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
        product_id=product_id_value_object.from_str("p-123"),
        product_version_id=product_version_id_value_object.from_str("vers-456"),
        product_version_name=product_version_name_value_object.from_str("v1.2.3"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
    )

    # ACT
    check_if_upgrade_available.handle(
        command=command, publisher=mock_publisher, logger=mock_logger, pp_qry_srv=mocked_qs
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_provisioned_product_repo.update_entity.assert_not_called()


def test_handle_when_new_version_is_different_region_should_not_mark_for_upgrade(
    get_provisioned_product, mock_publisher, mock_message_bus, mock_provisioned_product_repo, mock_logger
):
    # ARRANGE
    mocked_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    mocked_qs.get_all_provisioned_products_by_product_id.return_value = [
        get_provisioned_product(version_id="vers-123", version_name="1.0.0"),
        get_provisioned_product(version_id="vers-321", provisioned_product_id="pp-321", version_name="1.0.0"),
    ]

    command = check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
        product_id=product_id_value_object.from_str("p-123"),
        product_version_id=product_version_id_value_object.from_str("vers-456"),
        product_version_name=product_version_name_value_object.from_str("v1.2.3"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("eu-west-1"),
    )

    # ACT
    check_if_upgrade_available.handle(
        command=command, publisher=mock_publisher, logger=mock_logger, pp_qry_srv=mocked_qs
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_provisioned_product_repo.update_entity.assert_not_called()


def test_handle_when_new_version_is_different_stage_should_not_mark_for_upgrade(
    get_provisioned_product, mock_publisher, mock_message_bus, mock_provisioned_product_repo, mock_logger
):
    # ARRANGE
    mocked_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    mocked_qs.get_all_provisioned_products_by_product_id.return_value = [
        get_provisioned_product(version_id="vers-123", version_name="1.0.0"),
        get_provisioned_product(version_id="vers-321", provisioned_product_id="pp-321", version_name="1.0.0"),
    ]

    command = check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
        product_id=product_id_value_object.from_str("p-123"),
        product_version_id=product_version_id_value_object.from_str("vers-456"),
        product_version_name=product_version_name_value_object.from_str("v1.2.3"),
        stage=version_stage_value_object.from_str("qa"),
        region=region_value_object.from_str("us-east-1"),
    )

    # ACT
    check_if_upgrade_available.handle(
        command=command, publisher=mock_publisher, logger=mock_logger, pp_qry_srv=mocked_qs
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_provisioned_product_repo.update_entity.assert_not_called()


def test_handle_when_new_version_is_lower_should_not_mark_for_upgrade(
    get_provisioned_product, mock_publisher, mock_message_bus, mock_provisioned_product_repo, mock_logger
):
    # ARRANGE
    mocked_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    mocked_qs.get_all_provisioned_products_by_product_id.return_value = [
        get_provisioned_product(version_id="vers-123", version_name="1.0.0"),
        get_provisioned_product(version_id="vers-321", provisioned_product_id="pp-321", version_name="1.0.0"),
    ]

    command = check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
        product_id=product_id_value_object.from_str("p-123"),
        product_version_id=product_version_id_value_object.from_str("vers-456"),
        product_version_name=product_version_name_value_object.from_str("0.0.9"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
    )

    # ACT
    check_if_upgrade_available.handle(
        command=command, publisher=mock_publisher, logger=mock_logger, pp_qry_srv=mocked_qs
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_provisioned_product_repo.update_entity.assert_not_called()
