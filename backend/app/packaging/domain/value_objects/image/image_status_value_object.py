import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image


@dataclass(frozen=True)
class ImageStatusStatusValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ImageStatusStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Image status cannot be empty.")

    value = value.upper()

    if value not in image.ImageStatus.list():
        raise domain_exception.DomainException(f"Image status should be in {image.ImageStatus.list()}.")

    return ImageStatusStatusValueObject(value=value)
