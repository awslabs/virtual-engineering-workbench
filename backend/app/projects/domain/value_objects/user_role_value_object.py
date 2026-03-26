import typing

from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_assignment


class UserRoleValueObject:
    def __init__(self, value: project_assignment.Role) -> None:
        self._value = value

    @property
    def value(self) -> project_assignment.Role:
        return self._value


def from_str(value: typing.Optional[str]) -> UserRoleValueObject:
    if not value:
        raise domain_exception.DomainException("User role cannot be empty.")

    try:
        user_role = project_assignment.Role(value)
        return UserRoleValueObject(user_role)
    except ValueError:
        raise domain_exception.DomainException(f"User role cannot be {value}.")
