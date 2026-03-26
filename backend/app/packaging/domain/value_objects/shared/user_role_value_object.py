import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.shared.middleware.authorization import VirtualWorkbenchRoles


@dataclass(frozen=True)
class UserRoleValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> UserRoleValueObject:
    if not value:
        raise domain_exception.DomainException("User role cannot be empty.")

    value = value.upper()

    if value not in VirtualWorkbenchRoles.list():
        raise domain_exception.DomainException(
            "Not a valid user role. Should be ADMIN, PROGRAM_OWNER, POWER_USER, PRODUCT_CONTRIBUTOR, BETA_USER, PLATFORM_USER"
        )

    return UserRoleValueObject(value=value)
