import random
import string
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ProductIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ProductIdValueObject:
    if not value:
        raise domain_exception.DomainException("Product ID cannot be empty.")

    return ProductIdValueObject(value=value)


def generate_product_id() -> str:
    return "prod-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))
