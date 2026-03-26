import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Component version ID cannot be empty.")

    return ComponentVersionIdValueObject(value=value)
