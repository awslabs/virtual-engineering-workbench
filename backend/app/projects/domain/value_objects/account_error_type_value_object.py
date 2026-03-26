import typing

from app.projects.domain.exceptions import domain_exception


class AccountErrorTypeValueObject:
    def __init__(self, value: typing.Optional[str]) -> None:
        self._value = value

    @property
    def value(self) -> typing.Optional[str]:
        return self._value


def from_str(error: typing.Optional[str]) -> AccountErrorTypeValueObject:
    if not error:
        raise domain_exception.DomainException("Account error type should have error type.")

    return AccountErrorTypeValueObject(error)
