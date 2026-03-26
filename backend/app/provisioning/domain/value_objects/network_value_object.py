import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class NetworkValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> NetworkValueObject:
    if not value:
        raise domain_exception.DomainException("Network cannot be empty.")

    return NetworkValueObject(value=value)
