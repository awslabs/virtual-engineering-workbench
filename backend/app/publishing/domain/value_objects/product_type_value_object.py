import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product


@dataclass(frozen=True)
class ProductTypeValueObject:
    value: str

    def get_readable_value(self) -> str:
        return self.value.replace("_", " ").lower()


def from_str(value: typing.Optional[str]) -> ProductTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Product type cannot be empty.")

    value = value.upper()
    if value not in product.ProductType.list():
        raise domain_exception.DomainException(f"Not a valid product type. Should be in {product.ProductType.list()}")

    return ProductTypeValueObject(value=value)
