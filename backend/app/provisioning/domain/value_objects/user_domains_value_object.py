import typing

from app.shared.ddd import value_object


class UserDomainsValueObject(value_object.ValueObject):
    value: list[str]


def from_list(value: typing.Optional[list[str]]) -> UserDomainsValueObject:
    return UserDomainsValueObject(value=value or [])


def no_domains() -> UserDomainsValueObject:
    return UserDomainsValueObject(value=[])
