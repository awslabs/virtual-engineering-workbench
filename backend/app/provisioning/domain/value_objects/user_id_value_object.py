import enum
import typing
from urllib.parse import unquote

import pydantic

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class UserIdType(enum.StrEnum):
    User = "USER"
    Service = "SERVICE"


class UserIdValueObject(value_object.ValueObject):
    value: str = pydantic.Field(...)
    type: UserIdType = pydantic.Field(...)


def from_str(value: typing.Optional[str], type: UserIdType = UserIdType.User) -> UserIdValueObject:
    if not value:
        raise domain_exception.DomainException("User ID cannot be empty.")

    return UserIdValueObject(value=unquote(value), type=type)
