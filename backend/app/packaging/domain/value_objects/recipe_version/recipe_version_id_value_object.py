from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionIdValueObject:
    value: str


def from_str(value: str) -> RecipeVersionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version ID cannot be empty.")
    return RecipeVersionIdValueObject(value=value)
