import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionDescriptionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionDescriptionValueObject:
    if not re.match(r"^.{0,1024}$", value.strip()):
        raise domain_exception.DomainException("Component version description should be between 0 and 1024 characters.")

    return ComponentVersionDescriptionValueObject(value=value)
