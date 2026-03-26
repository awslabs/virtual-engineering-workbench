from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentSoftwareVersionValueObject:
    value: str


def from_str(value: str) -> ComponentSoftwareVersionValueObject:
    if not value:
        raise domain_exception.DomainException("Software version cannot be empty.")

    return ComponentSoftwareVersionValueObject(value=value)
