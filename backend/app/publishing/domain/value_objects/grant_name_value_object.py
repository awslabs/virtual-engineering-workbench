import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class GrantNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> GrantNameValueObject:
    if not value:
        raise domain_exception.DomainException("Grant name cannot be empty.")

    return GrantNameValueObject(value=value)
