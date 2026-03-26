import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class DateAndTimeValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> DateAndTimeValueObject:
    if not value:
        raise domain_exception.DomainException("Date and Time string cannot be empty.")

    return DateAndTimeValueObject(value=value)
