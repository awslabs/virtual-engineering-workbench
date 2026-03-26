from unittest import mock


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.provision_product.handle",
    autospec=True,
)
def test_handler_provisioned_product_launch_started(
    mocked_command_handler,
    generate_event,
    lambda_context,
    product_launch_started_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(detail_type="ProductLaunchStarted", detail=product_launch_started_event)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.stop_after_update.handle",
    autospec=True,
)
def test_handler_provisioned_product_updated(
    mocked_command_handler,
    generate_event,
    lambda_context,
    provisioned_product_updated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductUpgraded",
        detail=provisioned_product_updated_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.provision_product.handle",
    autospec=True,
)
def test_insufficient_capacity_reached_handler(
    mocked_command_handler,
    generate_event,
    lambda_context,
    insufficient_capacity_reached_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="InsufficientCapacityReached",
        detail=insufficient_capacity_reached_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.stop_for_update.handle",
    autospec=True,
)
def test_handler_provisioned_product_update_initialized(
    mocked_command_handler,
    generate_event,
    lambda_context,
    product_update_initialized_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductUpdateInitialized",
        detail=product_update_initialized_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.update_product.handle",
    autospec=True,
)
def test_handler_provisioned_product_stopped_for_upgrade(
    mocked_command_handler,
    generate_event,
    lambda_context,
    product_stopped_for_upgrade_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStoppedForUpgrade",
        detail=product_stopped_for_upgrade_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.update_product.handle",
    autospec=True,
)
def test_handler_provisioned_product_stopped_for_update(
    mocked_command_handler,
    generate_event,
    lambda_context,
    product_stopped_for_update_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStoppedForUpdate",
        detail=product_stopped_for_update_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.fail_update.handle",
    autospec=True,
)
def test_handler_provisioned_product_stop_for_upgrade_failed(
    mocked_command_handler,
    generate_event,
    lambda_context,
    product_stop_for_upgrade_failed_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStopForUpgradeFailed",
        detail=product_stop_for_upgrade_failed_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.deprovision_product.handle",
    autospec=True,
)
def test_handler_provisioned_product_remove_started(
    mocked_command_handler,
    generate_event,
    lambda_context,
    provisioned_product_removal_started_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductRemovalStarted",
        detail=provisioned_product_removal_started_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.deprovision_product.handle",
    autospec=True,
)
def test_handler_provisioned_product_remove_retried(
    mocked_command_handler,
    generate_event,
    lambda_context,
    provisioned_product_removal_retried_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductRemovalRetried",
        detail=provisioned_product_removal_retried_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.provisioned_product_state.start.handle",
    autospec=True,
)
def test_handler_provisioned_product_start_initiated(
    mocked_command_handler,
    generate_event,
    lambda_context,
    provisioned_product_start_initiated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStartInitiated",
        detail=provisioned_product_start_initiated_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()


@mock.patch(
    "app.provisioning.domain.command_handlers.provisioned_product_state.stop.handle",
    autospec=True,
)
def test_handler_provisioned_product_stop_initiated(
    mocked_command_handler,
    generate_event,
    lambda_context,
    provisioned_product_stop_initiated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStopInitiated",
        detail=provisioned_product_stop_initiated_event,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()
