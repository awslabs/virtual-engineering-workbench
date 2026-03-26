import json

import assertpy
import pytest

from app.projects.domain.command_handlers.project_accounts import fail_project_account_onboarding_command_handler
from app.projects.domain.commands.project_accounts import fail_project_account_onboarding_command
from app.projects.domain.model import project_account
from app.projects.domain.value_objects import (
    account_error_message_value_object,
    account_id_value_object,
    project_id_value_object,
)


def test_handle_when_account_is_onboarding_should_set_to_failed(
    mock_fail_project_account_onboarding_command,
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    sample_project_account_factory,
):
    # ARRANGE
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account_factory(
        account_status=project_account.ProjectAccountStatusEnum.OnBoarding
    )

    # ACT
    fail_project_account_onboarding_command_handler.handle(
        command=mock_fail_project_account_onboarding_command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()

    mock_account_repo.update_entity.assert_called_once()
    [pk, ent] = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(pk).is_equal_to(project_account.ProjectAccountPrimaryKey(projectId="123", id="321"))
    assertpy.assert_that(ent.accountStatus).is_equal_to("Failed")
    assertpy.assert_that(ent.lastOnboardingResult).is_equal_to("Failed")
    assertpy.assert_that(ent.lastOnboardingErrorMessage).is_equal_to("Test: Test cause")


def test_handle_when_account_is_reonboarding_should_set_to_active(
    mock_fail_project_account_onboarding_command,
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    sample_project_account_factory,
):
    # ARRANGE
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account_factory(
        account_status=project_account.ProjectAccountStatusEnum.ReOnboarding
    )

    # ACT
    fail_project_account_onboarding_command_handler.handle(
        command=mock_fail_project_account_onboarding_command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()

    mock_account_repo.update_entity.assert_called_once()
    [pk, ent] = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(pk).is_equal_to(project_account.ProjectAccountPrimaryKey(projectId="123", id="321"))
    assertpy.assert_that(ent.accountStatus).is_equal_to("Active")
    assertpy.assert_that(ent.lastOnboardingResult).is_equal_to("Failed")
    assertpy.assert_that(ent.lastOnboardingErrorMessage).is_equal_to("Test: Test cause")


def test_handle_when_error_is_task_failed_should_parse_task_cause(
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    sample_project_account_factory,
    ecs_task_error,
):
    # ARRANGE
    command = fail_project_account_onboarding_command.FailProjectAccountOnboarding(
        project_id=project_id_value_object.from_str("123"),
        account_id=account_id_value_object.from_str("321"),
        error=account_error_message_value_object.from_str(error="States.TaskFailed", cause=json.dumps(ecs_task_error)),
    )
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account_factory(
        account_status=project_account.ProjectAccountStatusEnum.OnBoarding
    )

    # ACT
    fail_project_account_onboarding_command_handler.handle(
        command=command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
    )

    # ASSERT
    mock_account_repo.update_entity.assert_called_once()
    [pk, ent] = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(ent.lastOnboardingErrorMessage).is_equal_to(
        "TaskFailedToStart: Unexpected EC2 error while attempting to Create Network Interface in subnet '': InsufficientFreeAddressesInSubnet"
    )


@pytest.mark.parametrize(
    "error, expected_error",
    [
        ("Some subnet-0011aabb error", "Some [REDACTED] error"),
        ("Some arn:aws:iam::001234567890:role/ExampleRole/Session error", "Some [REDACTED] error"),
        ("Some 001234567890 error", "Some [REDACTED] error"),
    ],
)
def test_handle_when_error_contains_aws_resource_ids_should_sanitize(
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    sample_project_account_factory,
    ecs_task_error_factory,
    error,
    expected_error,
):
    # ARRANGE
    command = fail_project_account_onboarding_command.FailProjectAccountOnboarding(
        project_id=project_id_value_object.from_str("123"),
        account_id=account_id_value_object.from_str("321"),
        error=account_error_message_value_object.from_str(
            error="States.TaskFailed", cause=json.dumps(ecs_task_error_factory(error_msg=error))
        ),
    )
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account_factory(
        account_status=project_account.ProjectAccountStatusEnum.OnBoarding
    )

    # ACT
    fail_project_account_onboarding_command_handler.handle(
        command=command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
    )

    # ASSERT
    mock_account_repo.update_entity.assert_called_once()
    [pk, ent] = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(ent.lastOnboardingErrorMessage).is_equal_to(f"TaskFailedToStart: {expected_error}")
