from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentSoftwareVendorValueObject:
    value: str


def from_str(value: str) -> ComponentSoftwareVendorValueObject:
    if not value:
        raise domain_exception.DomainException("Software vendor cannot be empty.")
    return ComponentSoftwareVendorValueObject(value=value)
