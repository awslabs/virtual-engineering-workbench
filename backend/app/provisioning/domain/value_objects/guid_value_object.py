import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class GuidValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> GuidValueObject:
    if not value:
        raise domain_exception.DomainException("Guid cannot be empty.")

    return GuidValueObject(value=value)
