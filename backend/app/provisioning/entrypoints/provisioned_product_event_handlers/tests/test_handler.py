from unittest import mock

import assertpy
import pytest

from app.provisioning.entrypoints.provisioned_product_event_handlers.model import product_cf_stack_status

IGNORED_STATUSES = [
    (e.value)
    for e in product_cf_stack_status.ProductCFStackStatus
    if e
    not in [
        product_cf_stack_status.ProductCFStackStatus.CREATE_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.CREATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.DELETE_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.DELETE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.ROLLBACK_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_FAILED,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_IN_PROGRESS,
    ]
]


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_launch.handle",
)
def test_provisioning_create_complete(
    mock_handler,
    lambda_context,
    generate_event,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event("CREATE_COMPLETE")

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_launch.handle",
)
def test_provisioning_create_complete_when_not_found_should_ignore(
    mock_handler,
    lambda_context,
    generate_event,
    mock_pp_qs,
):
    mock_pp_qs.get_by_sc_provisioned_product_id.return_value = None
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event("CREATE_COMPLETE")

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_not_called()
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_update.handle",
)
def test_provisioning_upgrade_complete(
    mock_handler,
    lambda_context,
    generate_event,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event("UPDATE_COMPLETE")

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_removal.handle",
)
def test_virtual_target_remove_complete(
    mock_handler,
    lambda_context,
    generate_event,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event("DELETE_COMPLETE")

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_launch.handle",
)
def test_provisioning_create_complete_when_resource_type_not_stack_should_ignore(
    mock_handler,
    lambda_context,
    generate_event,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event("CREATE_COMPLETE", "AWS::CloudFormation::SmthElse")

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_not_called()


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.fail_launch.handle",
)
@pytest.mark.parametrize(
    "received_status",
    [
        product_cf_stack_status.ProductCFStackStatus.CREATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.ROLLBACK_COMPLETE,
    ],
)
def test_provisioning_create_failed(
    mock_handler,
    lambda_context,
    generate_event,
    received_status,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event(received_status)

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.fail_update.handle",
)
@pytest.mark.parametrize(
    "received_status",
    [
        product_cf_stack_status.ProductCFStackStatus.UPDATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_FAILED,
    ],
)
def test_provisioning_upgrade_failed(
    mock_handler,
    lambda_context,
    generate_event,
    received_status,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event(received_status)

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.fail_removal.handle",
)
@pytest.mark.parametrize(
    "received_status",
    [
        product_cf_stack_status.ProductCFStackStatus.DELETE_FAILED,
    ],
)
def test_virtual_target_removal_failed(
    mock_handler,
    lambda_context,
    generate_event,
    received_status,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event(received_status)

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    assertpy.assert_that(kwargs.get("command").provisioned_product_id.value).is_equal_to("pp-123")
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with("pp-00000000")


@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.complete_launch.handle",
)
@mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.fail_launch.handle",
)
@pytest.mark.parametrize("received_status", IGNORED_STATUSES)
def test_when_status_is_not_terminal_should_ignore(
    create_complete_handler,
    create_failed_handler,
    lambda_context,
    generate_event,
    received_status,
    mock_pp_qs,
):
    from app.provisioning.entrypoints.provisioned_product_event_handlers import handler

    handler.dependencies.provisioned_products_query_service = mock_pp_qs

    # Prepare event
    minimal_event = generate_event(received_status)

    # Act
    handler.handler(minimal_event, lambda_context)

    # Assert
    create_complete_handler.assert_not_called()
    create_failed_handler.assert_not_called()
