from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


def test_handler_when_ec2_is_runing_handles_complete_provisioned_product_start(
    mock_dependencies,
    generate_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    mock_pp_qs,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event("running")

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_start_command_handler.assert_called_once_with(
        complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
        )
    )
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with(sc_provisioned_product_id="pp-12345")


def test_handler_when_ec2_is_stopped_and_not_updating_handles_complete_provisioned_product_stop(
    mock_dependencies,
    generate_event,
    lambda_context,
    complete_provisioned_product_stop_command_handler,
    mock_pp_qs,
    get_provisioned_product,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event("stopped")
    mock_pp_qs.get_by_sc_provisioned_product_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Stopping
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_stop_command_handler.assert_called_once_with(
        complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with(sc_provisioned_product_id="pp-12345")


def test_handler_when_ec2_is_stopped_and_updating_handles_update_provisioned_product(
    mock_dependencies,
    generate_event,
    lambda_context,
    update_provisioned_product_command_handler,
    mock_pp_qs,
    get_provisioned_product,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event("stopped")
    mock_pp_qs.get_by_sc_provisioned_product_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Updating
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    update_provisioned_product_command_handler.assert_called_once_with(
        update_provisioned_product_command.UpdateProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_sc_provisioned_product_id.assert_called_once_with(sc_provisioned_product_id="pp-12345")


def test_handler_stopping_event_no_command_handler_called(
    mock_dependencies,
    generate_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event("stopping")

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_start_command_handler.assert_not_called()
    complete_provisioned_product_stop_command_handler.assert_not_called()


def test_handler_pending_event_no_command_handler_called(
    mock_dependencies,
    generate_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event("pending")

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_start_command_handler.assert_not_called()
    complete_provisioned_product_stop_command_handler.assert_not_called()


# container tests


def test_handler_when_container_is_running_handles_complete_provisioned_product_start(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    mock_pp_qs,
    get_provisioned_product,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("running")
    mock_pp_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_start_command_handler.assert_called_once_with(
        complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
        )
    )
    mock_pp_qs.get_by_id.assert_called_once_with(provisioned_product_id="vt-12345")


def test_handler_when_container_is_stopped_and_not_updating_handles_complete_provisioned_product_stop(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    complete_provisioned_product_stop_command_handler,
    mock_pp_qs,
    get_provisioned_product,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("stopped")
    mock_pp_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Stopped,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_stop_command_handler.assert_called_once_with(
        complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_id.assert_called_once_with(provisioned_product_id="vt-12345")


#
def test_handler_when_container_is_stopped_and_updating_handles_update_provisioned_product(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    update_provisioned_product_command_handler,
    mock_pp_qs,
    get_provisioned_product,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("stopped")
    mock_pp_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Updating,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    update_provisioned_product_command_handler.assert_called_once_with(
        update_provisioned_product_command.UpdateProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_id.assert_called_once_with(provisioned_product_id="vt-12345")


def test_handler_stopping_event_container_command_handler_called(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
    get_provisioned_product,
    mock_pp_qs,
    update_provisioned_product_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("stopping")
    mock_pp_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Running,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_stop_command_handler.assert_called_once_with(
        complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_id.assert_called_once_with(provisioned_product_id="vt-12345")


def test_handler_deprovisioning_event_container_command_handler_called(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
    get_provisioned_product,
    mock_pp_qs,
    update_provisioned_product_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("DEPROVISIONING")
    mock_pp_qs.get_by_id.return_value = get_provisioned_product(
        provisioned_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Running,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_stop_command_handler.assert_called_once_with(
        complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        )
    )
    mock_pp_qs.get_by_id.assert_called_once_with(provisioned_product_id="vt-12345")


def test_handler_pending_event_no_container_command_handler_called(
    mock_dependencies,
    generate_ecs_task_state_change_event,
    lambda_context,
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.provisioned_product_state_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_ecs_task_state_change_event("pending")

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    complete_provisioned_product_start_command_handler.assert_not_called()
    complete_provisioned_product_stop_command_handler.assert_not_called()
