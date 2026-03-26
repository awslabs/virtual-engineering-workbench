from datetime import datetime, timezone

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class StartHourValueObject(value_object.ValueObject):
    value: int


def from_str(value: str) -> StartHourValueObject:
    if not value:
        start_hour = int(datetime.now(timezone.utc).strftime("%H"))
    elif not value.isdigit():
        raise domain_exception.DomainException("Start hour should be a number.")
    elif int(value) > 23 or int(value) < 0:
        raise domain_exception.DomainException("Start hour should be between 0 and 23.")
    else:
        start_hour = int(value)

    return StartHourValueObject(value=start_hour)
