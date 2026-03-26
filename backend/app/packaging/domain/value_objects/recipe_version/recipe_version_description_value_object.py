import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionDescriptionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeVersionDescriptionValueObject:
    if not re.match(r"^[A-Za-z0-9_ -]{1,100}$", value.strip()):
        raise domain_exception.DomainException(
            "Recipe version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."
        )

    return RecipeVersionDescriptionValueObject(value=value)
