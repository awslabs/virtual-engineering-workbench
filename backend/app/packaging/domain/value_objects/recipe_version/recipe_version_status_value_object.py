import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version


@dataclass(frozen=True)
class RecipeVersionStatusValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeVersionStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version status cannot be empty.")

    value = value.upper()

    if value not in recipe_version.RecipeVersionStatus.list():
        raise domain_exception.DomainException(
            f"Recipe version status should be in {recipe_version.RecipeVersionStatus.list()}."
        )

    return RecipeVersionStatusValueObject(value=value)
