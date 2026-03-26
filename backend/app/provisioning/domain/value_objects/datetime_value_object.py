import typing
from datetime import datetime

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class DatetimeValueObject(value_object.ValueObject):
    value: datetime


def from_str(value: typing.Optional[str]) -> DatetimeValueObject:
    if not value:
        raise domain_exception.DomainException("Datetime cannot be empty.")

    datetime_object = datetime.fromisoformat(value.rstrip("Z") + "+00:00")

    return DatetimeValueObject(value=datetime_object)
