import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ImageIdValueObject:
    if not value:
        raise domain_exception.DomainException("Image ID cannot be empty.")

    return ImageIdValueObject(value=value)
