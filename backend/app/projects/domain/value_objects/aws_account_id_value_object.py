import re
import typing

from app.projects.domain.exceptions import domain_exception


class AWSAccountIDValueObject:
    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value


def from_str(value: typing.Optional[str]) -> AWSAccountIDValueObject:
    if not value:
        raise domain_exception.DomainException("Account ID cannot be empty.")

    if not re.match(r"^\d{12}$", value):
        raise domain_exception.DomainException("Account ID must contain 12 digits.")

    return AWSAccountIDValueObject(value)
