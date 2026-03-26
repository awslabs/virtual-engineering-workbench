import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageDigestValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ImageDigestValueObject:
    if not value:
        raise domain_exception.DomainException("Container Image Digest cannot be empty.")

    return ImageDigestValueObject(value=value)
