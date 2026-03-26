from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry


@dataclass(frozen=True)
class RecipeVersionComponentsVersionsValueObject:
    value: list[ComponentVersionEntry]


def from_list(component_versions: list[ComponentVersionEntry]) -> RecipeVersionComponentsVersionsValueObject:
    for component_version in component_versions:
        if not component_version.componentId:
            raise domain_exception.DomainException("Component ID cannot be empty.")
        if not component_version.componentName:
            raise domain_exception.DomainException("Component name cannot be empty.")
        if not component_version.componentVersionId:
            raise domain_exception.DomainException("Component version ID cannot be empty.")
        if not component_version.componentVersionName:
            raise domain_exception.DomainException("Component version name cannot be empty.")
        if not component_version.order:
            raise domain_exception.DomainException("Order cannot be empty.")
        if not component_version.componentVersionType:
            raise domain_exception.DomainException("Component version type cannot be empty.")

    return RecipeVersionComponentsVersionsValueObject(value=component_versions)
