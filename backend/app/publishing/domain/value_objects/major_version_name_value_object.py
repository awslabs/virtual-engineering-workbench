import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class MajorVersionNameValueObject:
    value: int


def from_int(value: typing.Optional[int]) -> MajorVersionNameValueObject:
    if not value:
        raise domain_exception.DomainException("Major version name cannot be empty.")

    return MajorVersionNameValueObject(value=value)
