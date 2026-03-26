import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class CurrencyValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> CurrencyValueObject:
    if not value:
        raise domain_exception.DomainException("Currency can not be empty")

    return CurrencyValueObject(value=value)
