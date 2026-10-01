import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionParentImageProductIdValueObject:
    value: str


def from_str(value: str) -> RecipeVersionParentImageProductIdValueObject:
    pattern = r"^prod-[a-z0-9]+$"
    if not re.match(pattern, value):
        raise domain_exception.DomainException(f"Parent image product ID should match {pattern} pattern.")

    return RecipeVersionParentImageProductIdValueObject(value=value)
