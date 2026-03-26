import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class VersionNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionNameValueObject:
    if not value:
        raise domain_exception.DomainException("Version name cannot be empty.")

    return VersionNameValueObject(value=value)
