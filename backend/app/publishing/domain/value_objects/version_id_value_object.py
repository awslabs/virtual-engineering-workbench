import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class VersionIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Version Id cannot be empty.")

    return VersionIdValueObject(value=value)
