from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image.image_constants import ImageArchitecture

VALID_ARCHITECTURES = ImageArchitecture.list()


@dataclass(frozen=True)
class ArchitectureValueObject:
    value: str


def from_str(value: str) -> ArchitectureValueObject:
    if not value:
        raise domain_exception.DomainException("Architecture cannot be empty.")
    if value not in VALID_ARCHITECTURES:
        raise domain_exception.DomainException(f"Invalid architecture: {value}. Must be one of {VALID_ARCHITECTURES}.")
    return ArchitectureValueObject(value=value)
