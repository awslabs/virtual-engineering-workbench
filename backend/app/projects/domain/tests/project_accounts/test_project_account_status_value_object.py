import assertpy
import pytest

from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_account
from app.projects.domain.value_objects import account_status_value_object


# a test case to test the from_str function of the account_status_value_object module
def test_can_create_activate_account_status_value_object_from_str():
    assertpy.assert_that(account_status_value_object.from_key_str("Active").value).is_equal_to(
        project_account.ProjectAccountStatusEnum.Active
    )


def test_can_create_inactive_account_status_value_object_from_str():
    assertpy.assert_that(account_status_value_object.from_key_str("Inactive").value).is_equal_to(
        project_account.ProjectAccountStatusEnum.Inactive
    )


def test_from_value_str():
    assertpy.assert_that(account_status_value_object.from_value_str("Inactive").value).is_equal_to(
        project_account.ProjectAccountStatusEnum.Inactive
    )


def test_raises_exception_when_invalid_account_status_value_str():
    with pytest.raises(domain_exception.DomainException):
        account_status_value_object.from_value_str("InvalidValue")


def test_raises_exception_when_invalid_account_status_key_str():
    with pytest.raises(domain_exception.DomainException):
        account_status_value_object.from_key_str("InvalidKey")


def test_raises_exception_when_invalid_account_status_tools_str():
    with pytest.raises(domain_exception.DomainException):
        account_status_value_object.from_tools_str("InvalidTools")
