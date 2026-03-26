from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)


@dataclass(frozen=True)
class MandatoryComponentsVersionsValueObject:
    value: list[ComponentVersionEntry]


def from_list(
    component_versions: list[ComponentVersionEntry],
) -> MandatoryComponentsVersionsValueObject:
    returned_component_versions = []

    for component_version in component_versions:
        if not component_version.componentId:
            raise domain_exception.DomainException("Component ID cannot be empty.")
        if not component_version.componentVersionId:
            raise domain_exception.DomainException("Component version ID cannot be empty.")
        if not component_version.order:
            raise domain_exception.DomainException("Order cannot be empty.")

        returned_component_versions.append(
            ComponentVersionEntry(
                componentId=component_version.componentId,
                componentVersionId=component_version.componentVersionId,
                componentName=component_version.componentName,
                componentVersionName=component_version.componentVersionName,
                order=component_version.order,
                position=component_version.position,
            )
        )
    return MandatoryComponentsVersionsValueObject(value=returned_component_versions)
