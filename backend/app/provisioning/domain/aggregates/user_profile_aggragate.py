import logging
from datetime import datetime, timezone

from app.provisioning.domain.commands.user_profile import (
    cleanup_user_profile_command,
    update_user_profile_command,
)
from app.provisioning.domain.events.user_profile import (
    user_profile_cleaned_up,
    user_profile_updated,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import maintenance_window, user_profile
from app.provisioning.domain.ports import projects_query_service
from app.provisioning.domain.value_objects import user_id_value_object
from app.shared.ddd import aggregate


class UserProfileAggregate(aggregate.Aggregate):
    def __init__(
        self,
        logger: logging.Logger,
        user_profile_entity: user_profile.UserProfile | None = None,
        maintenance_windows: list[maintenance_window.MaintenanceWindow] | None = None,
    ):
        super().__init__()
        self._logger = logger
        self._user_profile = user_profile_entity.copy(deep=True) if user_profile_entity else None
        self._original_user_profile = user_profile_entity.copy(deep=True) if user_profile_entity else None
        self._maintenance_windows: list[maintenance_window.MaintenanceWindow] | None = (
            maintenance_windows.copy() if maintenance_windows else None
        )
        self._original_maintenance_windows: list[maintenance_window.MaintenanceWindow] | None = (
            maintenance_windows.copy() if maintenance_windows else None
        )

    def update(self, command: update_user_profile_command.UpdateUserProfileCommand):
        """
        Creates or updates the user profile and maintenance window entities
        """
        self.__raise_if_not(user_id=command.user_id)

        new_maintenance_windows = [
            maintenance_window.MaintenanceWindow(
                day=single_mw.day,
                startTime=single_mw.startTime,
                endTime=single_mw.endTime,
                userId=command.user_id.value,
            )
            for single_mw in command.preferred_maintenance_windows.value
        ]

        if self._user_profile:
            self._user_profile.preferredRegion = command.preferred_region.value
            self._user_profile.preferredNetwork = command.preferred_network.value
            self._user_profile.preferredMaintenanceWindows = new_maintenance_windows
        else:
            current_time = datetime.now(timezone.utc).isoformat()
            self._user_profile = user_profile.UserProfile(
                userId=command.user_id.value,
                preferredRegion=command.preferred_region.value,
                preferredNetwork=command.preferred_network.value,
                createDate=current_time,
                lastUpdateDate=current_time,
                preferredMaintenanceWindows=new_maintenance_windows,
            )

        self._maintenance_windows = new_maintenance_windows

        self._publish(
            user_profile_updated.UserProfileUpdated(
                userId=command.user_id.value,
            )
        )

    def cleanup(
        self,
        command: cleanup_user_profile_command.CleanUpUserProfileCommand,
        projects_qry_srv: projects_query_service.ProjectsQueryService,
    ):
        """
        Deletes the user profile and maintenance windows for the given user if user has no more assignments left
        """
        self.__raise_if_not(user_id=command.user_id)

        if not self._user_profile:
            self._logger.warning("User profile does not exist.")
            return

        user_assignments_count = projects_qry_srv.get_user_assignments_count(command.user_id.value)
        if user_assignments_count == 0:
            self._user_profile = None
            self._maintenance_windows = None
            self._publish(
                user_profile_cleaned_up.UserProfileCleanedUp(
                    userId=command.user_id.value,
                )
            )

    def __raise_if_not(
        self,
        user_id: user_id_value_object.UserIdValueObject | None = None,
    ):
        if self._user_profile and user_id.value.upper().strip() != self._user_profile.userId.upper().strip():
            raise domain_exception.DomainException("User is not allowed to modify the requested user profile.")

    def _repository_actions(self):
        # Create/Update/Delete user profile entity
        if not self._original_user_profile and self._user_profile:
            self._user_profile.lastUpdateDate = datetime.now(timezone.utc).isoformat()
            self._pending_updates.append(
                lambda uow: uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).add(
                    self._user_profile
                )
            )
        elif self._original_user_profile and self._user_profile:
            self._user_profile.lastUpdateDate = datetime.now(timezone.utc).isoformat()
            self._pending_updates.append(
                lambda uow: uow.get_repository(
                    user_profile.UserProfilePrimaryKey, user_profile.UserProfile
                ).update_entity(
                    pk=user_profile.UserProfilePrimaryKey(
                        userId=self._user_profile.userId,
                    ),
                    entity=self._user_profile,
                )
            )
        elif self._original_user_profile and not self._user_profile:
            self._pending_updates.append(
                lambda uow, user_id=self._original_user_profile.userId: uow.get_repository(
                    user_profile.UserProfilePrimaryKey, user_profile.UserProfile
                ).remove(
                    pk=user_profile.UserProfilePrimaryKey(
                        userId=user_id,
                    )
                )
            )
        self._original_user_profile = self._user_profile.copy(deep=True) if self._user_profile else None

        # Update maintenance window entities
        self._remove_old_maintenance_window()
        self._insert_new_maintenance_window()
        self._handle_maintenance_window_cleanup()

        self._original_maintenance_windows = self._maintenance_windows.copy() if self._maintenance_windows else None

    def _remove_old_maintenance_window(self):
        # Remove old maintenance windows if exists
        if self._maintenance_windows and self._original_maintenance_windows:
            for mw in self._original_maintenance_windows:
                if mw in self._maintenance_windows:
                    continue
                self._pending_updates.append(
                    lambda uow, _mw=mw: uow.get_repository(
                        maintenance_window.MaintenanceWindowPrimaryKey,
                        maintenance_window.MaintenanceWindow,
                    ).remove(
                        pk=maintenance_window.MaintenanceWindowPrimaryKey(
                            day=_mw.day,
                            nearestStartHour=_mw.nearestStartHour,
                            userId=_mw.userId,
                        )
                    )
                )

    def _insert_new_maintenance_window(self):
        # Insert new maintenance windows
        if self._maintenance_windows:
            for mw in self._maintenance_windows:
                if self._original_maintenance_windows and mw in self._original_maintenance_windows:
                    continue
                self._pending_updates.append(
                    lambda uow, _mw=mw: uow.get_repository(
                        maintenance_window.MaintenanceWindowPrimaryKey,
                        maintenance_window.MaintenanceWindow,
                    ).add(_mw)
                )

    def _handle_maintenance_window_cleanup(self):
        # Remove all maintenance windows for cleanup
        if not self._maintenance_windows and self._original_maintenance_windows:
            for mw in self._original_maintenance_windows:
                self._pending_updates.append(
                    lambda uow, _mw=mw: uow.get_repository(
                        maintenance_window.MaintenanceWindowPrimaryKey,
                        maintenance_window.MaintenanceWindow,
                    ).remove(
                        pk=maintenance_window.MaintenanceWindowPrimaryKey(
                            day=_mw.day,
                            nearestStartHour=_mw.nearestStartHour,
                            userId=_mw.userId,
                        )
                    )
                )
