import re
from dataclasses import dataclass
from typing import Optional

from app.packaging.domain.exceptions import domain_exception

PRODUCT_CODE_PATTERN = re.compile(r"^[a-z0-9]{13,25}$")


@dataclass(frozen=True)
class ProductCodeValueObject:
    value: str


def from_str(value: Optional[str]) -> ProductCodeValueObject:
    if not value:
        raise domain_exception.DomainException("Product code cannot be empty.")
    if not PRODUCT_CODE_PATTERN.match(value):
        raise domain_exception.DomainException(
            f"Invalid product code format: {value}. Must be 13-25 lowercase alphanumeric characters."
        )
    return ProductCodeValueObject(value=value)
