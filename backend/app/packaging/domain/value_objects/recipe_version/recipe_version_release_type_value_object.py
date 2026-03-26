from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version


@dataclass(frozen=True)
class RecipeVersionReleaseTypeValueObject:
    value: str


def from_str(value: str) -> RecipeVersionReleaseTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version release type cannot be empty.")

    value = value.upper()

    if value not in recipe_version.RecipeVersionReleaseType.list():
        raise domain_exception.DomainException(
            f"Recipe version release type should be in {recipe_version.RecipeVersionReleaseType.list()}."
        )

    return RecipeVersionReleaseTypeValueObject(value=value)
