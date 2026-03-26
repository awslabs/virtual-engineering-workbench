import re
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ProductNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ProductNameValueObject:
    if not value:
        raise domain_exception.DomainException("Product name cannot be empty.")

    if not re.match(r"^[A-Za-z0-9_ -]{1,50}$", value):
        raise domain_exception.DomainException(
            "Product name should be between 1 and 50 characters in alphanumeric, space( ), underscore(_) and hyphen(-)"
        )

    return ProductNameValueObject(value=value)
