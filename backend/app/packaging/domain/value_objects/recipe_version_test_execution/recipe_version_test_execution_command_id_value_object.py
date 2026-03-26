import typing
import uuid
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionTestExecutionCommandIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeVersionTestExecutionCommandIdValueObject:
    if not value:
        raise domain_exception.DomainException("Command ID cannot be empty.")

    try:
        uuid.UUID(value)
    except ValueError:
        raise domain_exception.DomainException("Command ID is not a valid UUID.")

    return RecipeVersionTestExecutionCommandIdValueObject(value=value)
