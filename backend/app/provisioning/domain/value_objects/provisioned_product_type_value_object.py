import typing
from dataclasses import dataclass
from functools import reduce

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioned_product


@dataclass(frozen=True)
class ProvisionedProductTypeValueObject:
    value: str

    def get_readable_value(self) -> str:
        return self.value.replace("_", " ").lower()


def from_str(value: typing.Optional[str]) -> ProvisionedProductTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Provisioned product type cannot be empty.")

    # Convert PascalCase or camelCase to upper SNAKE_CASE
    value = reduce(lambda x, y: x + ("_" if y.isupper() else "") + y, value).upper()
    if value not in provisioned_product.ProvisionedProductType.list():
        raise domain_exception.DomainException(
            f"Not a valid provisioned product type. Should be in {provisioned_product.ProvisionedProductType.list()}"
        )

    return ProvisionedProductTypeValueObject(value=value)
