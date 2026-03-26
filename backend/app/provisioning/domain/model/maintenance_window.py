from enum import Enum

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class WeekDay(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def list():
        return list(map(lambda p: p.value, WeekDay))


class MaintenanceWindowPrimaryKey(unit_of_work.PrimaryKey):
    day: WeekDay = Field(..., title="Day")
    nearestStartHour: int = Field(..., title="NearestStartHour")
    userId: str = Field(..., title="UserId")


class MaintenanceWindow(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    day: WeekDay = Field(..., title="Day")
    startTime: str = Field(..., title="StartTime")
    endTime: str = Field(..., title="EndTime")

    @property
    def nearestStartHour(self) -> int:
        """
        This property returns the nearest start hour for the given maintenance window start time.
        eg if startTime is "09:00" then it returns 9.
        eg if startTime is "09:30" then it returns 10.
        """
        start_time = self.startTime.replace(":", "")
        return int(start_time[:2]) if int(start_time) % 100 == 0 else int(start_time[:2]) + 1
