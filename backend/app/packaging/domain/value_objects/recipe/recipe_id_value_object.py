import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeIdValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe ID cannot be empty.")

    return RecipeIdValueObject(value=value)
