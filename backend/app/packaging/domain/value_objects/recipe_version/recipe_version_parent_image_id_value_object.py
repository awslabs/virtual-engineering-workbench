import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionParentImageIdValueObject:
    value: str


def from_str(value: str) -> RecipeVersionParentImageIdValueObject:
    pattern = r"^image-[a-z0-9]{8}$"
    if not value or not re.match(pattern, value):
        raise domain_exception.DomainException(f"Parent image ID should match {pattern} pattern.")

    return RecipeVersionParentImageIdValueObject(value=value)
