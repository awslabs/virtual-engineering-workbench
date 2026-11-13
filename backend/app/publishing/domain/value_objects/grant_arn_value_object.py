import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class GrantArnValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> GrantArnValueObject:
    if not value:
        raise domain_exception.DomainException("Grant ARN cannot be empty.")

    return GrantArnValueObject(value=value)
