import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class VersionIdValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> VersionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Version Id cannot be empty.")

    return VersionIdValueObject(value=value)
