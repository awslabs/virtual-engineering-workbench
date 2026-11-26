import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

PARENT_IMAGE_ID_PATTERN = r"^image-[a-z0-9]+$"


@dataclass(frozen=True)
class RecipeVersionParentImageIdValueObject:
    """An image imported into the project (AWS_PUBLISHED_AMI) that a recipe version builds on."""

    value: str


def from_str(value: str) -> RecipeVersionParentImageIdValueObject:
    if not value or len(value) > 64 or not re.fullmatch(PARENT_IMAGE_ID_PATTERN, value):
        raise domain_exception.DomainException(f"Parent image ID should match {PARENT_IMAGE_ID_PATTERN} pattern.")

    return RecipeVersionParentImageIdValueObject(value=value)
