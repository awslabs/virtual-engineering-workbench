import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ProjectIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ProjectIdValueObject:
    if not value:
        raise domain_exception.DomainException("Project ID cannot be empty.")

    return ProjectIdValueObject(value=value)
