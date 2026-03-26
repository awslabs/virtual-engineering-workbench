import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class EventNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> EventNameValueObject:
    if not value:
        raise domain_exception.DomainException("Event name cannot be empty.")

    return EventNameValueObject(value=value)
