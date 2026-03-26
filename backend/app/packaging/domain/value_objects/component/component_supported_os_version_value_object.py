import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component


@dataclass(frozen=True)
class ComponentSupportedOsVersionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentSupportedOsVersionValueObject:
    if not value:
        raise domain_exception.DomainException("Component supported OS version cannot be empty.")

    if value not in component.ComponentSupportedOsVersions.list():
        raise domain_exception.DomainException(
            f"Component supported OS version should be in {component.ComponentSupportedOsVersions.list()}."
        )

    return ComponentSupportedOsVersionValueObject(value=value)
