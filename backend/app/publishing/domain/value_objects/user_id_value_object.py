import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class UserIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> UserIdValueObject:
    if not value:
        raise domain_exception.DomainException("User ID cannot be empty.")

    return UserIdValueObject(value=value)
