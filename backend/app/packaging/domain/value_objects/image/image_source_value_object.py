from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image.image_constants import ImageSource


@dataclass(frozen=True)
class ImageSourceValueObject:
    value: str


def from_str(value: str) -> ImageSourceValueObject:
    try:
        source = ImageSource(value)
    except ValueError:
        raise domain_exception.DomainException(
            f"Invalid image source: {value}. Must be one of {[e.value for e in ImageSource]}."
        )
    return ImageSourceValueObject(value=source.value)
