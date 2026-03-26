import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageTagValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ImageTagValueObject:
    if not value:
        raise domain_exception.DomainException("Container Image Tag cannot be empty.")

    return ImageTagValueObject(value=value)
