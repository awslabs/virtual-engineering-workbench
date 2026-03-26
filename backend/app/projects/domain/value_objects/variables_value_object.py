import typing

from app.projects.domain.exceptions import domain_exception


class VariablesValueObject:
    def __init__(self, value: dict[str, str]) -> None:
        self._value = value

    @property
    def value(self) -> dict[str, str]:
        return self._value


def from_dict(value: typing.Optional[dict[str, str]]) -> VariablesValueObject:
    if not value:
        raise domain_exception.DomainException("Variables cannot be empty.")

    if not all(key and value for key, value in value.items()):
        raise domain_exception.DomainException("Keys and values cannot be empty.")

    return VariablesValueObject(value)
