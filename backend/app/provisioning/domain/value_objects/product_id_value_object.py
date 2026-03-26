import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class ProductIdValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> ProductIdValueObject:
    if not value:
        raise domain_exception.DomainException("Product ID cannot be empty.")

    return ProductIdValueObject(value=value)


def from_list(value: typing.List[str]) -> typing.List[ProductIdValueObject]:
    if not value:
        raise domain_exception.DomainException("Product ID cannot be empty.")

    return [from_str(v) for v in value]
