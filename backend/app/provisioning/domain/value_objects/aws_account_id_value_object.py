import re
import typing
from dataclasses import dataclass

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


@dataclass(frozen=True)
class AWSAccountIDValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> AWSAccountIDValueObject:
    if not value:
        raise domain_exception.DomainException("Account ID cannot be empty.")

    if not re.match(r"^\d{12}$", value):
        raise domain_exception.DomainException("Account ID must contain 12 digits.")

    return AWSAccountIDValueObject(value=value)
