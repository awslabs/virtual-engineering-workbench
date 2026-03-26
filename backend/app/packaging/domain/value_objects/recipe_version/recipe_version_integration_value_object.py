from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionIntegrationValueObject:
    value: str


def from_str(value: str) -> RecipeVersionIntegrationValueObject:
    if not value:
        raise domain_exception.DomainException("Integration value cannot be empty.")
    return RecipeVersionIntegrationValueObject(value=value)


def from_str_array(values: list[str]) -> list[RecipeVersionIntegrationValueObject]:
    return [from_str(v) for v in values]
