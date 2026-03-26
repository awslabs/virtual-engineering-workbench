import typing

from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_account


class AccountStatusValueObject:
    def __init__(self, value: project_account.ProjectAccountStatusEnum) -> None:
        self._value = value

    @property
    def value(self) -> project_account.ProjectAccountStatusEnum:
        return self._value


ACCOUNT_STATUS_MAP = {
    "Account Onboarding Initiated": project_account.ProjectAccountStatusEnum.OnBoarding,
    "Account Onboarding Complete": project_account.ProjectAccountStatusEnum.Active,
    "Account Onboarding Failed": project_account.ProjectAccountStatusEnum.Failed,
    "Account Onboarding Error": project_account.ProjectAccountStatusEnum.Failed,
}


# a function called from_str that takes a string and returns an AccountStatusValueObject
def from_key_str(value: typing.Optional[str]) -> AccountStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Account Status cannot be empty.")

    if value not in project_account.ProjectAccountStatusEnum.__members__:
        raise domain_exception.DomainException(f"Account Status {value} is not valid.")

    return AccountStatusValueObject(project_account.ProjectAccountStatusEnum[value])


def from_value_str(value: typing.Optional[str]) -> AccountStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Account Status cannot be empty.")

    mapping = project_account.ProjectAccountStatusEnum.__members__

    for e in mapping:
        if value == mapping[e].value:
            return AccountStatusValueObject(mapping[e])

    raise domain_exception.DomainException(f"{value} is not a valid status.")


def from_tools_str(value: typing.Optional[str]) -> AccountStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Account Status cannot be empty.")

    if value not in ACCOUNT_STATUS_MAP:
        raise domain_exception.DomainException(f"{value} is not a valid status update message.")

    return AccountStatusValueObject(ACCOUNT_STATUS_MAP[value])
