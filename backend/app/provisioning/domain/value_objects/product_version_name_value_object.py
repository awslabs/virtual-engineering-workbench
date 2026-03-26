import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class ProductVersionNameValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> ProductVersionNameValueObject:
    if not value:
        raise domain_exception.DomainException("Product version name cannot be empty.")

    return ProductVersionNameValueObject(value=value)
