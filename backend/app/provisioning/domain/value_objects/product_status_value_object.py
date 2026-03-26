from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import product_status
from app.shared.ddd import value_object


class ProductStatusValueObject(value_object.ValueObject):
    value: product_status.ProductStatus


def from_str(value: str) -> ProductStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Product status cannot be empty.")

    if value.upper() not in product_status.ProductStatus.list():
        raise domain_exception.DomainException(
            f"Not a valid product status. Should be in {product_status.ProductStatus.list()}"
        )

    return ProductStatusValueObject(value=product_status.ProductStatus(value.upper()))
