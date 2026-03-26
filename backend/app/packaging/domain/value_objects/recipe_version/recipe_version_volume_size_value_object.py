from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionVolumeSizeValueObject:
    value: str


def from_str(value: str) -> RecipeVersionVolumeSizeValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version volume size cannot be empty.")
    try:
        if not 8 <= int(value) <= 500:
            raise domain_exception.DomainException("Recipe version volume size must be included between 8 and 500 GB.")
    except ValueError:
        raise domain_exception.DomainException("Recipe version volume size must be a valid integer.")

    return RecipeVersionVolumeSizeValueObject(value=value)
