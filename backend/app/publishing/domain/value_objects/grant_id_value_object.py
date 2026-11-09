import typing
import uuid
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class GrantIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> GrantIdValueObject:
    if not value:
        raise domain_exception.DomainException("Grant ID cannot be empty.")

    return GrantIdValueObject(value=value)


def generate() -> GrantIdValueObject:
    return GrantIdValueObject(value=f"lg-{uuid.uuid4().hex[:8]}")
