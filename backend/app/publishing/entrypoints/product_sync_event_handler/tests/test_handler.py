def test_products_versions_sync_handler_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_sync_requested,
    mock_product_version_sync_command_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.product_sync_event_handler import handler

    handler.dependencies = mock_dependencies

    # ACT
    handler.handler(product_version_sync_requested, lambda_context)

    # ASSERT
    mock_product_version_sync_command_handler.assert_called_once()
