import json
import os

import assertpy
import pytest

from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
    fail_project_account_onboarding_command,
)
from app.projects.entrypoints.account_onboarding.model import step_function_model


def test_handle_setup_prerequisites_resources(mock_dependencies, setup_prerequisites_resources_command_mock):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SetupPrerequisitesResourcesRequest(accountId="123456789012", region="us-east-1")
    os.environ["EVENT"] = json.dumps(request.model_dump(by_alias=True))

    # ACT
    result = handler.main()

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    setup_prerequisites_resources_command_mock.assert_called_once()


def test_handle_setup_prerequisites_resources_when_raises_should_send_failure(
    mock_dependencies, setup_prerequisites_resources_command_mock, sfn_service_mock
):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SetupPrerequisitesResourcesRequest(accountId="123456789012", region="us-east-1")
    os.environ["EVENT"] = json.dumps(request.model_dump(by_alias=True))
    os.environ["TASK_TOKEN"] = "test-token"

    setup_prerequisites_resources_command_mock.side_effect = Exception("Test Error")

    # ACT
    with pytest.raises(Exception):
        handler.main()

    # ASSERT
    sfn_service_mock.send_callback_failure.assert_called_once_with(
        callback_token="test-token", error_type="Exception", error_message="Test Error"
    )


def test_handle_setup_dynamic_resources(mock_dependencies, lambda_context, setup_dynamic_resources_command_mock):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SetupDynamicResourcesRequest(accountId="123456789012", region="us-east-1")

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    setup_dynamic_resources_command_mock.assert_called_once()


def test_handle_setup_static_resources(mock_dependencies, setup_static_resources_command_mock):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SetupStaticResourcesRequest(accountId="123456789012", region="us-east-1")
    os.environ["EVENT"] = json.dumps(request.model_dump(by_alias=True))

    # ACT
    result = handler.main()

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    setup_static_resources_command_mock.assert_called_once()


def test_handle_setup_static_resources_when_raises_should_send_failure(
    mock_dependencies, setup_static_resources_command_mock, sfn_service_mock
):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SetupStaticResourcesRequest(accountId="123456789012", region="us-east-1")
    os.environ["EVENT"] = json.dumps(request.model_dump(by_alias=True))
    os.environ["TASK_TOKEN"] = "test-token"

    setup_static_resources_command_mock.side_effect = Exception("Test Error")

    # ACT
    with pytest.raises(Exception):
        handler.main()

    # ASSERT
    sfn_service_mock.send_callback_failure.assert_called_once_with(
        callback_token="test-token", error_type="Exception", error_message="Test Error"
    )


def test_handle_complete_onboarding(mock_dependencies, complete_onboard_command_mock, lambda_context):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.CompleteProjectAccountOnboardingRequest(
        projectId="proj-123",
        projectAccountId="acc-123",
    )

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    complete_onboard_command_mock.assert_called_once()
    [cmd] = complete_onboard_command_mock.call_args.args
    assertpy.assert_that(cmd).is_type_of(complete_project_account_onboarding_command.CompleteProjectAccountOnboarding)
    assertpy.assert_that(cmd.project_id.value).is_equal_to("proj-123")
    assertpy.assert_that(cmd.account_id.value).is_equal_to("acc-123")


def test_handle_fail_onboarding(mock_dependencies, fail_onboard_command_mock, lambda_context):
    # ARRANGE
    from app.projects.entrypoints.account_onboarding import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.FailProjectAccountOnboardingRequest(
        projectId="proj-123",
        projectAccountId="acc-123",
        error="Test error",
        cause="Test cause",
    )

    # ACT
    result = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    fail_onboard_command_mock.assert_called_once()
    [cmd] = fail_onboard_command_mock.call_args.args
    assertpy.assert_that(cmd).is_type_of(fail_project_account_onboarding_command.FailProjectAccountOnboarding)
    assertpy.assert_that(cmd.project_id.value).is_equal_to("proj-123")
    assertpy.assert_that(cmd.account_id.value).is_equal_to("acc-123")
    assertpy.assert_that(cmd.error.error).is_equal_to("Test error")
    assertpy.assert_that(cmd.error.cause).is_equal_to("Test cause")
