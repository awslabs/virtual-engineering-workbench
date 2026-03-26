from app.provisioning.domain.command_handlers.user_profile import clean_up
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.events.user_profile import user_profile_cleaned_up
from app.provisioning.domain.model import maintenance_window, user_profile
from app.provisioning.domain.value_objects import user_id_value_object


def test_clean_up_user_profile_command_handler_cleans_up_user_profile_if_no_more_assignments_left(
    mock_logger,
    mock_publisher,
    mock_unit_of_work,
    mock_message_bus,
    mock_user_profile_repo,
    mock_maintenance_window_repo,
    mock_maintenance_windows_qs,
    mock_projects_qs,
):
    # ARRANGE
    command = cleanup_user_profile_command.CleanUpUserProfileCommand(
        user_id=user_id_value_object.from_str("T0011AA"),
    )

    # ACT
    clean_up.handle(
        command=command,
        publisher=mock_publisher,
        uow=mock_unit_of_work,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        projects_qry_srv=mock_projects_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(user_profile_cleaned_up.UserProfileCleanedUp(userId="T0011AA"))
    mock_unit_of_work.commit.assert_called_once()
    mock_user_profile_repo.remove.assert_called_once_with(
        user_profile.UserProfilePrimaryKey(userId="T0011AA"),
    )
    mock_maintenance_window_repo.remove.assert_called_once_with(
        maintenance_window.MaintenanceWindowPrimaryKey(
            day=maintenance_window.WeekDay.MONDAY, nearestStartHour=0, userId="T0011AA"
        )
    )


def test_clean_up_user_profile_command_handler_skips_clean_up_if_more_assignments_left(
    mock_logger,
    mock_publisher,
    mock_unit_of_work,
    mock_message_bus,
    mock_user_profile_repo,
    mock_maintenance_window_repo,
    mock_maintenance_windows_qs,
    mock_projects_qs,
):
    # ARRANGE
    command = cleanup_user_profile_command.CleanUpUserProfileCommand(
        user_id=user_id_value_object.from_str("T0011AA"),
    )
    mock_projects_qs.get_user_assignments_count.return_value = 1

    # ACT
    clean_up.handle(
        command=command,
        publisher=mock_publisher,
        uow=mock_unit_of_work,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        projects_qry_srv=mock_projects_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    mock_user_profile_repo.remove.assert_not_called()
    mock_maintenance_window_repo.remove.assert_not_called()
