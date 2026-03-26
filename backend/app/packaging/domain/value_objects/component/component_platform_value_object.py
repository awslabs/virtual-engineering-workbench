import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component


@dataclass(frozen=True)
class ComponentPlatformValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentPlatformValueObject:
    if not value:
        raise domain_exception.DomainException("Component platform cannot be empty.")

    if value not in component.ComponentPlatform.list():
        raise domain_exception.DomainException(f"Component platform should be in {component.ComponentPlatform.list()}.")

    return ComponentPlatformValueObject(value=value)
