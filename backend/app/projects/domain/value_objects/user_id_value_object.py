import enum
import typing
from urllib.parse import unquote

from app.projects.domain.exceptions import domain_exception


class UserIdType(enum.StrEnum):
    User = "USER"
    Service = "SERVICE"


class UserIdValueObject:
    def __init__(self, value: str, type: UserIdType) -> None:
        self.__value = value
        self.__type = type

    @property
    def value(self) -> str:
        return self.__value

    @property
    def type(self) -> UserIdType:
        return self.__type


def from_str(value: typing.Optional[str], type: UserIdType = UserIdType.User) -> UserIdValueObject:
    if not value:
        raise domain_exception.DomainException("User ID cannot be empty.")

    return UserIdValueObject(unquote(value), type)
