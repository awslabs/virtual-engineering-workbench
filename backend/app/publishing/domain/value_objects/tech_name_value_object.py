import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class TechNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> TechNameValueObject:
    if not value:
        raise domain_exception.DomainException("Tech Name cannot be empty.")

    return TechNameValueObject(value=value)
