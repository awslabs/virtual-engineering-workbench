import re
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class VersionDescriptionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionDescriptionValueObject:
    if not re.match(r"^[A-Za-z0-9_ -]{0,100}$", value):
        raise domain_exception.DomainException(
            "Version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)"
        )

    return VersionDescriptionValueObject(value=value)
