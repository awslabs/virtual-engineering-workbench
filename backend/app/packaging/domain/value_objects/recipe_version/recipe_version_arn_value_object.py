import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionArnValueObject:
    value: str


def from_str(value: str) -> RecipeVersionArnValueObject:
    pattern = r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image-recipe/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+$"
    if not re.match(pattern, value):
        raise domain_exception.DomainException(f"Recipe version ARN should match {pattern} pattern.")

    return RecipeVersionArnValueObject(value=value)
