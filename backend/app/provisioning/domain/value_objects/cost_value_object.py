import typing
from decimal import Decimal

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class CostValueObject(value_object.ValueObject):
    value: Decimal


def from_decimal(value: typing.Optional[Decimal]) -> CostValueObject:
    if value is None:
        raise domain_exception.DomainException("Cost can not be empty")

    return CostValueObject(value=value)
