import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentDescriptionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentDescriptionValueObject:
    if not re.match(r"^.{0,1024}$", value.strip()):
        raise domain_exception.DomainException("Component description should be between 0 and 1024 characters.")

    return ComponentDescriptionValueObject(value=value)
