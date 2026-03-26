from datetime import datetime, timezone

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import maintenance_window
from app.shared.ddd import value_object

WEEKDAYS = maintenance_window.WeekDay.list()


class WeekDayValueObject(value_object.ValueObject):
    value: maintenance_window.WeekDay


def from_str(value: str) -> WeekDayValueObject:
    if not value:
        current_day = datetime.now(timezone.utc).strftime("%A").upper()
        day = next(
            maintenance_window.WeekDay(week_day)
            for week_day in maintenance_window.WeekDay
            if week_day == current_day.upper()
        )
    elif value.upper() not in WEEKDAYS:
        raise domain_exception.DomainException(f"Week day not valid, should be in {WEEKDAYS}.")
    else:
        day = maintenance_window.WeekDay(value.upper())

    return WeekDayValueObject(value=day)
