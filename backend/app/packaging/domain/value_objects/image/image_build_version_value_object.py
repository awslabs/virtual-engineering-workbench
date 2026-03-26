from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageBuildVersionValueObject:
    value: int


def from_int(value: int) -> ImageBuildVersionValueObject:
    if not (value and value > 0):
        raise domain_exception.DomainException("Image build version must be a positive integer.")

    return ImageBuildVersionValueObject(value=value)
