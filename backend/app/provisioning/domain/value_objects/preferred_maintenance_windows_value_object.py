import typing

from pydantic import Field

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import maintenance_window
from app.shared.ddd import value_object

WEEKDAYS = maintenance_window.WeekDay.list()


class MaintenanceWindow(value_object.ValueObject):
    day: maintenance_window.WeekDay = Field(..., title="Day")
    startTime: str = Field(..., title="StartTime")
    endTime: str = Field(..., title="EndTime")


class PreferredPreferredMaintenanceWindowsValueObject(value_object.ValueObject):
    value: typing.List[MaintenanceWindow]


def from_list(value) -> PreferredPreferredMaintenanceWindowsValueObject:
    if not value and not isinstance(value, typing.List):
        raise domain_exception.DomainException("Preferred Maintenance Windows cannot be empty.")
    else:
        for item in value:
            if not item:
                raise domain_exception.DomainException("Maintenance Window cannot be empty.")
            if not item.day and item.day.upper() not in WEEKDAYS:
                raise domain_exception.DomainException(f"Maintenance Window day not valid, should be in {WEEKDAYS}.")
            if not item.startTime:
                raise domain_exception.DomainException(f"Maintenance Window start time cannot be empty for {item.day}")
            if not item.endTime:
                raise domain_exception.DomainException(f"Maintenance Window end time cannot be empty for {item.day}")

    return PreferredPreferredMaintenanceWindowsValueObject(
        value=[MaintenanceWindow.model_validate(mw if isinstance(mw, dict) else mw.model_dump()) for mw in value]
    )
