from abc import ABC, abstractmethod

from app.provisioning.domain.model import maintenance_window


class MaintenanceWindowsQueryService(ABC):
    @abstractmethod
    def get_maintenance_windows_by_user_id(self, user_id: str) -> list[maintenance_window.MaintenanceWindow]: ...

    def get_maintenance_windows_by_time(
        self, day: maintenance_window.WeekDay, start_hour: int
    ) -> list[maintenance_window.MaintenanceWindow]: ...
