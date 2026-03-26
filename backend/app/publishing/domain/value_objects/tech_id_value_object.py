import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class TechIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> TechIdValueObject:
    if not value:
        raise domain_exception.DomainException("Tech ID cannot be empty.")

    return TechIdValueObject(value=value)
