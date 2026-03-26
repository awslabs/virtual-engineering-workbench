import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionTestExecutionInstanceIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeVersionTestExecutionInstanceIdValueObject:
    if not re.match(r"^i-[a-z0-9]{17}$", value):
        raise domain_exception.DomainException("Recipe version test execution instance ID must be a valid instance ID.")

    return RecipeVersionTestExecutionInstanceIdValueObject(value=value)
