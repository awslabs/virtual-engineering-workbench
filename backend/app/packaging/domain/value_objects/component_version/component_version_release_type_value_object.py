import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version


@dataclass(frozen=True)
class ComponentVersionReleaseTypeValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionReleaseTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Component version release type cannot be empty.")

    value = value.upper()

    if value not in component_version.ComponentVersionReleaseType.list():
        raise domain_exception.DomainException(
            f"Component version release type should be in {component_version.ComponentVersionReleaseType.list()}."
        )

    return ComponentVersionReleaseTypeValueObject(value=value)
