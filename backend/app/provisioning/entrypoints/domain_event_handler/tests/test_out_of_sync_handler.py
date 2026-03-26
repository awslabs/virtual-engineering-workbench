def test_handler_provisioned_product_running(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_running_payload,
    mock_complete_provisioned_product_start_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync", detail=provisioned_product_status_out_of_sync_running_payload
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_complete_provisioned_product_start_command_handler.assert_called_once()


def test_handler_provisioned_product_stopped(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_stopped_payload,
    mock_complete_provisioned_product_stop_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync", detail=provisioned_product_status_out_of_sync_stopped_payload
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_complete_provisioned_product_stop_command_handler.assert_called_once()


def test_handler_provisioned_product_provisioned(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_provisioned_payload,
    mock_complete_provisioned_product_launch_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_provisioned_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_complete_provisioned_product_launch_command_handler.assert_called_once()


def test_handler_provisioned_product_provision_failed(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_provisioning_failed_payload,
    mock_fail_provisioned_product_launch_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_provisioning_failed_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_fail_provisioned_product_launch_command_handler.assert_called_once()


def test_handler_provisioned_product_terminated(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_terminated_payload,
    mock_complete_provisioned_product_removal_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_terminated_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_complete_provisioned_product_removal_command_handler.assert_called_once()


def test_handler_provisioned_product_terminate_failed(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_terminate_failed_payload,
    mock_fail_provisioned_product_removal_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_terminate_failed_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_fail_provisioned_product_removal_command_handler.assert_called_once()


def test_handler_provisioned_product_updated(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_updated_payload,
    mock_complete_provisioned_product_update_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_updated_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_complete_provisioned_product_update_command_handler.assert_called_once()


def test_handler_provisioned_product_update_failed(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_updating_failed_payload,
    mock_fail_provisioned_product_update_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_updating_failed_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_fail_provisioned_product_update_command_handler.assert_called_once()


def test_handler_provisioned_product_configuration_failed(
    mock_dependencies,
    generate_event,
    lambda_context,
    provisioned_product_status_out_of_sync_configuration_failed_payload,
    mock_fail_provisioned_product_configuration_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProvisionedProductStatusOutOfSync",
        detail=provisioned_product_status_out_of_sync_configuration_failed_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_fail_provisioned_product_configuration_command_handler.assert_called_once()
