from unittest import mock

from freezegun import freeze_time

from app.provisioning.domain.command_handlers.user_profile import update
from app.provisioning.domain.commands.user_profile import update_user_profile_command
from app.provisioning.domain.events.user_profile import user_profile_updated
from app.provisioning.domain.model import maintenance_window, user_profile
from app.provisioning.domain.value_objects import (
    network_value_object,
    preferred_maintenance_windows_value_object,
    region_value_object,
    user_id_value_object,
)


@freeze_time("2024-01-18")
def test_update_user_profile_command_handler_updates_profile_and_maintenance_windows_if_exists(
    mock_logger,
    mock_publisher,
    mock_unit_of_work,
    mock_message_bus,
    mock_user_profile_repo,
    mock_maintenance_window_repo,
    mock_maintenance_windows_qs,
):
    # ARRANGE
    maintenance_windows = [
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.MONDAY, startTime="00:00", endTime="04:00", userId="T0011AA"
        ),
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.THURSDAY, startTime="04:00", endTime="08:00", userId="T0011AA"
        ),
    ]

    command = update_user_profile_command.UpdateUserProfileCommand(
        user_id=user_id_value_object.from_str("T0011AA"),
        preferred_region=region_value_object.from_str("eu-west-3"),
        preferred_network=network_value_object.from_str("y"),
        preferred_maintenance_windows=preferred_maintenance_windows_value_object.from_list(maintenance_windows),
    )

    # ACT
    update.handle(
        command=command,
        publisher=mock_publisher,
        uow=mock_unit_of_work,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(user_profile_updated.UserProfileUpdated(userId="T0011AA"))
    mock_unit_of_work.commit.assert_called_once()
    mock_user_profile_repo.update_entity.assert_called_once_with(
        user_profile.UserProfilePrimaryKey(userId="T0011AA"),
        user_profile.UserProfile(
            userId="T0011AA",
            preferredRegion="eu-west-3",
            preferredNetwork="y",
            preferredMaintenanceWindows=maintenance_windows,
            createDate="2024-01-18T00:00:00+00:00",
            lastUpdateDate="2024-01-18T00:00:00+00:00",
        ),
    )
    mock_maintenance_window_repo.add.assert_called_once_with(
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.THURSDAY, startTime="04:00", endTime="08:00", userId="T0011AA"
        ),
    )


@freeze_time("2024-01-18")
def test_update_user_profile_command_handler_creates_profile_and_maintenance_windows_if_does_not_exist(
    mock_logger,
    mock_publisher,
    mock_unit_of_work,
    mock_message_bus,
    mock_user_profile_repo,
    mock_maintenance_window_repo,
    mock_maintenance_windows_qs,
):
    # ARRANGE
    mock_user_profile_repo.get.return_value = None
    mock_maintenance_windows_qs.get_maintenance_windows_by_user_id.return_value = None
    maintenance_windows = [
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.MONDAY, startTime="00:00", endTime="04:00", userId="T0011AA"
        ),
        maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.THURSDAY, startTime="04:00", endTime="08:00", userId="T0011AA"
        ),
    ]

    command = update_user_profile_command.UpdateUserProfileCommand(
        user_id=user_id_value_object.from_str("T0011AA"),
        preferred_region=region_value_object.from_str("eu-west-3"),
        preferred_network=network_value_object.from_str("y"),
        preferred_maintenance_windows=preferred_maintenance_windows_value_object.from_list(maintenance_windows),
    )

    # ACT
    update.handle(
        command=command,
        publisher=mock_publisher,
        uow=mock_unit_of_work,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(user_profile_updated.UserProfileUpdated(userId="T0011AA"))
    mock_unit_of_work.commit.assert_called_once()
    mock_user_profile_repo.add.assert_called_once_with(
        user_profile.UserProfile(
            userId="T0011AA",
            preferredRegion="eu-west-3",
            preferredNetwork="y",
            preferredMaintenanceWindows=maintenance_windows,
            createDate="2024-01-18T00:00:00+00:00",
            lastUpdateDate="2024-01-18T00:00:00+00:00",
        ),
    )
    mock_maintenance_window_repo.add.assert_has_calls(
        [
            mock.call(
                maintenance_window.MaintenanceWindow(
                    day=maintenance_window.WeekDay.MONDAY, startTime="00:00", endTime="04:00", userId="T0011AA"
                ),
            ),
            mock.call(
                maintenance_window.MaintenanceWindow(
                    day=maintenance_window.WeekDay.THURSDAY, startTime="04:00", endTime="08:00", userId="T0011AA"
                ),
            ),
        ]
    )
