from unittest import mock

from app.provisioning.domain.commands.product_provisioning import remove_provisioned_product_command
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)


def test_handler_user_unassigned(
    mock_dependencies,
    generate_event,
    lambda_context,
    user_unassigned_event,
    mock_remove_provisioned_product_command_handler,
    mock_clean_up_user_profile_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.projects_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(detail_type="UserUnAssigned", detail=user_unassigned_event)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_remove_provisioned_product_command_handler.assert_has_calls(
        [
            mock.call(
                remove_provisioned_product_command.RemoveProvisionedProductCommand(
                    provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
                    project_id=project_id_value_object.from_str("proj-123"),
                    user_id=user_id_value_object.from_str("T0011AA"),
                ),
            ),
            mock.call(
                remove_provisioned_product_command.RemoveProvisionedProductCommand(
                    provisioned_product_id=provisioned_product_id_value_object.from_str("pp-234"),
                    project_id=project_id_value_object.from_str("proj-123"),
                    user_id=user_id_value_object.from_str("T0011AA"),
                )
            ),
            mock.call(
                remove_provisioned_product_command.RemoveProvisionedProductCommand(
                    provisioned_product_id=provisioned_product_id_value_object.from_str("pp-345"),
                    project_id=project_id_value_object.from_str("proj-123"),
                    user_id=user_id_value_object.from_str("T0011AA"),
                )
            ),
        ]
    )
    mock_clean_up_user_profile_command_handler.assert_called_once_with(
        cleanup_user_profile_command.CleanUpUserProfileCommand(user_id=user_id_value_object.from_str("T0011AA"))
    )
