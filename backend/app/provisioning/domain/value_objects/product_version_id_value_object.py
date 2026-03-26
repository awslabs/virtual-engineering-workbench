import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class ProductVersionIdValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> ProductVersionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Product Version ID cannot be empty.")

    return ProductVersionIdValueObject(value=value)
