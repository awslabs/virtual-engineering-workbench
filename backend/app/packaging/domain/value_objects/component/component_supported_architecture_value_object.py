import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component


@dataclass(frozen=True)
class ComponentSupportedArchitectureValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentSupportedArchitectureValueObject:
    if not value:
        raise domain_exception.DomainException("Component supported architecture cannot be empty.")

    if value not in component.ComponentSupportedArchitectures.list():
        raise domain_exception.DomainException(
            f"Component supported architecture should be in {component.ComponentSupportedArchitectures.list()}."
        )

    return ComponentSupportedArchitectureValueObject(value=value)
