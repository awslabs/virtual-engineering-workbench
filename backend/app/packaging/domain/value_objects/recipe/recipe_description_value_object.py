import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeDescriptionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeDescriptionValueObject:
    if not re.match(r"^[A-Za-z0-9_ -]{1,100}$", value.strip()):
        raise domain_exception.DomainException(
            "Recipe description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."
        )
    return RecipeDescriptionValueObject(value=value)
