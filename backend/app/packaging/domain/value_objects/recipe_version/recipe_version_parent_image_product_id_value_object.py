import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

# AWS Marketplace has two product ID formats: "prod-<base36>" and, for many AMI products
# (Canonical's Ubuntu images, for example), a lowercase UUID.
PARENT_IMAGE_PRODUCT_ID_PATTERN = r"^(prod-[a-z0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"


@dataclass(frozen=True)
class RecipeVersionParentImageProductIdValueObject:
    value: str


def from_str(value: str) -> RecipeVersionParentImageProductIdValueObject:
    if not value or len(value) > 64 or not re.fullmatch(PARENT_IMAGE_PRODUCT_ID_PATTERN, value):
        raise domain_exception.DomainException(
            f"Parent image product ID should match {PARENT_IMAGE_PRODUCT_ID_PATTERN} pattern."
        )

    return RecipeVersionParentImageProductIdValueObject(value=value)
