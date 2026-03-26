import typing
import uuid
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionTestExecutionIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionTestExecutionIdValueObject:
    if not value:
        raise domain_exception.DomainException("Component version test execution ID cannot be empty.")

    try:
        uuid.UUID(value)
    except ValueError:
        raise domain_exception.DomainException("Component version test execution ID is not a valid UUID.")

    return ComponentVersionTestExecutionIdValueObject(value=value)
