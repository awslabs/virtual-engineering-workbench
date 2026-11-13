from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageNameValueObject:
    value: str


def from_str(value: str) -> ImageNameValueObject:
    if not value or not value.strip():
        raise domain_exception.DomainException("Image name cannot be empty.")
    if len(value) > 100:
        raise domain_exception.DomainException("Image name must be 100 characters or fewer.")
    return ImageNameValueObject(value=value.strip())
