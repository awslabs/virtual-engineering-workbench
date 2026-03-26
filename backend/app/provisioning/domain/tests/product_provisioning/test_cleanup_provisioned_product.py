import json

import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import (
    cleanup_provisioned_products,
)
from app.provisioning.domain.commands.product_provisioning import (
    cleanup_provisioned_products_command,
)
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_dormant_cleanup_failed,
)
from app.provisioning.domain.model import product_status
from app.provisioning.domain.value_objects import (
    provisioned_product_cleanup_value_object,
)


@pytest.fixture()
def mock_command():
    return cleanup_provisioned_products_command.CleanupProvisionedProductsCommand(
        provisioned_product_cleanup_config=provisioned_product_cleanup_value_object.from_json_str(
            json.dumps(
                {
                    "pp-cleanup-alert": 7,
                    "pp-cleanup": 14,
                    "pp-experimental-cleanup-alert": 5,
                    "pp-experimental-cleanup": 7,
                },
            )
        )
    )


@freeze_time("2023-12-15")
def test_handler_finds_dormant_provisioned_products_publish_fail_event_on_error(
    mock_logger,
    mock_publisher,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_provisioned_product,
    mock_command,
):
    # ARRANGE
    mock_provisioned_products_qs.get_all_provisioned_products.return_value = [
        get_provisioned_product(
            provisioned_product_id="pp-1",
            status=product_status.ProductStatus.Stopped,
            created_by="SF44515",
            # Wrong date
            last_update_date="2023-12-32T00:00:00+00:00",
            private_ip="127.0.0.1",
            instance_id="i-1",
        )
    ]
    # ACT
    cleanup_provisioned_products.handle(
        logger=mock_logger,
        publisher=mock_publisher,
        provisioned_products_qry_srv=mock_provisioned_products_qs,
        command=mock_command,
    )
    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_dormant_cleanup_failed.ProvisionedProductDormantCleanupFailed()
    )
