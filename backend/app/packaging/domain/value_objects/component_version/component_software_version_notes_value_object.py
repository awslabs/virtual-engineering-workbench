from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentSoftwareVersionNotesValueObject:
    value: str


def from_str(value: str) -> ComponentSoftwareVersionNotesValueObject:
    if not value:
        raise domain_exception.DomainException("Notes cannot be empty.")
    return ComponentSoftwareVersionNotesValueObject(value=value)
