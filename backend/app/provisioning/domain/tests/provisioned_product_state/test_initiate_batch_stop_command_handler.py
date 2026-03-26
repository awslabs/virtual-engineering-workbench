from unittest import mock

import assertpy
import pytest

from app.provisioning.domain.command_handlers.provisioned_product_state import (
    initiate_batch_stop,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_batch_stop_command,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_stop_initiated,
)
from app.provisioning.domain.model import product_status, provisioned_product_output


@pytest.fixture()
def mock_command():
    return initiate_provisioned_product_batch_stop_command.InitiateProvisionedProductBatchStopCommand()


def test_initiate_batch_stop_should_stop_all_running_products_except_protected(
    mock_command,
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    get_provisioned_product,
    mock_message_bus,
    mock_unit_of_work,
):

    # ARRANGE
    mock_virtual_targets_qs.get_all_provisioned_products.return_value = [
        get_provisioned_product(
            provisioned_product_id="pp-1",
            status=product_status.ProductStatus.Running,
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="FeatureToggles",
                    outputValue='[{"feature": "DCVConnectionOptions", "enabled": true}, {"feature": "AutoStopProtection", "enabled": true}]',
                    description="Enabled features for this workbench",
                ),
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="OtherKey",
                    outputValue="some value",
                    description="Other description",
                ),
            ],
        ),
        get_provisioned_product(
            provisioned_product_id="pp-2",
            status=product_status.ProductStatus.Running,
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="FeatureToggles",
                    outputValue='[{"feature": "DCVConnectionOptions", "enabled": true}, {"feature": "AutoStopProtection", "enabled": false}]',
                    description="Enabled features for this workbench",
                ),
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="OtherKey",
                    outputValue="some value",
                    description="Other description",
                ),
            ],
        ),
        get_provisioned_product(
            provisioned_product_id="pp-3",
            status=product_status.ProductStatus.Running,
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="FeatureToggles",
                    outputValue='[{ "feature": "DCVConnectionOptions", "enabled": true }]',
                    description="Enabled features for this workbench",
                ),
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="OtherKey",
                    outputValue="some value",
                    description="Other description",
                ),
            ],
        ),
        get_provisioned_product(
            provisioned_product_id="pp-4",
            status=product_status.ProductStatus.Running,
        ),
    ]

    # ACT
    initiate_batch_stop.handle(
        command=mock_command,
        publisher=mock_publisher,
        logger=mock_logger,
        pp_qry_srv=mock_virtual_targets_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_has_calls(
        [
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-2")),
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-3")),
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-4")),
        ]
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(3)


def test_initiate_batch_stop_should_stop_all_running_products_except_where_iser_disabled_autostop(
    mock_command,
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    get_provisioned_product,
    mock_message_bus,
    mock_unit_of_work,
):

    # ARRANGE
    mock_virtual_targets_qs.get_all_provisioned_products.return_value = [
        get_provisioned_product(
            provisioned_product_id="pp-1",
            status=product_status.ProductStatus.Running,
        ),
        get_provisioned_product(
            provisioned_product_id="pp-2",
            status=product_status.ProductStatus.Running,
        ),
        get_provisioned_product(
            provisioned_product_id="pp-3",
            status=product_status.ProductStatus.Running,
        ),
        get_provisioned_product(
            provisioned_product_id="pp-4",
            status=product_status.ProductStatus.Running,
        ),
    ]

    # ACT
    initiate_batch_stop.handle(
        command=mock_command,
        publisher=mock_publisher,
        logger=mock_logger,
        pp_qry_srv=mock_virtual_targets_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_has_calls(
        [
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-1")),
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-2")),
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-3")),
            mock.call(provisioned_product_stop_initiated.ProvisionedProductStopInitiated(provisionedProductId="pp-4")),
        ]
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(4)
