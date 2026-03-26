import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionParentImageUpstreamIdValueObject:
    value: str


def from_str(value: str) -> RecipeVersionParentImageUpstreamIdValueObject:
    if not re.match(r"^ami-[a-z0-9]{17}$", value):
        raise domain_exception.DomainException("Parent image upstream id should match ami-[a-z|0-9]{0,17} pattern.")

    return RecipeVersionParentImageUpstreamIdValueObject(value=value)
