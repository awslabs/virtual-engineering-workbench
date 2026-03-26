import typing

from app.projects.domain.exceptions import domain_exception


class AccountIdValueObject:
    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value


def from_str(value: typing.Optional[str]) -> AccountIdValueObject:
    if not value:
        raise domain_exception.DomainException("Account ID cannot be empty.")

    return AccountIdValueObject(value)
