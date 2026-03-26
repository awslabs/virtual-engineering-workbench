import typing
from datetime import datetime

from app.projects.domain.exceptions import domain_exception


class DateValueObject:
    def __init__(self, value: datetime) -> None:
        self._value = value

    @property
    def value(self) -> datetime:
        return self._value


def from_str(value: typing.Optional[str]) -> DateValueObject:
    if not value:
        raise domain_exception.DomainException("Date cannot be empty.")

    datetime_object = datetime.fromisoformat(value.rstrip("Z") + "+00:00")

    return DateValueObject(datetime_object)
