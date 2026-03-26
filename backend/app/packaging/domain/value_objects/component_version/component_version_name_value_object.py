import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionNameValueObject:
    if not value:
        raise domain_exception.DomainException("Component version name cannot be empty.")

    return ComponentVersionNameValueObject(value=value)
