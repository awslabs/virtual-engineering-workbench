import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version


@dataclass(frozen=True)
class ComponentVersionStatusValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Component version status cannot be empty.")

    value = value.upper()

    if value not in component_version.ComponentVersionStatus.list():
        raise domain_exception.DomainException(
            f"Component version status should be in {component_version.ComponentVersionStatus.list()}."
        )

    return ComponentVersionStatusValueObject(value=value)
