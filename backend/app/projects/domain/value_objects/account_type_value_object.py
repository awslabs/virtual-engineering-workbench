import typing
from enum import Enum

from app.projects.domain.exceptions import domain_exception


class AccountTypeEnum(str, Enum):
    USER = "USER"
    TOOLCHAIN = "TOOLCHAIN"

    def __str__(self):
        return str(self.value)


class AccountTypeValueObject:
    def __init__(self, value: AccountTypeEnum) -> None:
        self._value = value

    @property
    def value(self) -> AccountTypeEnum:
        return self._value


def from_str(value: typing.Optional[str]) -> AccountTypeValueObject:
    if not value:
        raise domain_exception.DomainException("Account Type cannot be empty.")
    if value.upper().strip() == "USER":
        return AccountTypeValueObject(AccountTypeEnum.USER)
    if value.upper().strip() == "TOOLCHAIN":
        return AccountTypeValueObject(AccountTypeEnum.TOOLCHAIN)
    raise domain_exception.DomainException("Unknown product type. Can be 'USER' or 'TOOLCHAIN'")
