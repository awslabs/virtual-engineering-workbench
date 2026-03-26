import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class ProductNameValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> ProductNameValueObject:
    if not value:
        raise domain_exception.DomainException("Product name cannot be empty.")

    return ProductNameValueObject(value=value)
