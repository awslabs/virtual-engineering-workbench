import assertpy

from app.projects.domain.command_handlers.project_accounts import (
    complete_project_account_onboarding_command_handler,
)
from app.projects.domain.events.project_accounts import project_account_on_boarded
from app.projects.domain.model import project_account


def test_handle_should_fetch_and_store_account_parameters(
    mock_complete_project_account_onboarding_command,
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    mock_parameters_qs,
    message_bus_mock,
):
    # ARRANGE
    mock_parameters_qs.get_parameters_by_path.return_value = {
        "/param/path/1": "param-value",
    }

    # ACT
    complete_project_account_onboarding_command_handler.handle(
        command=mock_complete_project_account_onboarding_command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
        parameters_qs=mock_parameters_qs,
        account_parameters_path="/param/path",
        message_bus=message_bus_mock,
    )

    # ASSERT
    mock_parameters_qs.get_parameters_by_path.assert_called_once()
    (path, boto_cfg) = mock_parameters_qs.get_parameters_by_path.call_args.kwargs.values()
    assertpy.assert_that(path).is_equal_to("/param/path")
    assertpy.assert_that(boto_cfg.aws_account_id).is_equal_to("123")
    assertpy.assert_that(boto_cfg.aws_region).is_equal_to("us-east-1")

    mock_uow_2.commit.assert_called_once()

    mock_account_repo.update_entity.assert_called_once()
    [pk, ent] = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(pk).is_equal_to(project_account.ProjectAccountPrimaryKey(projectId="123", id="321"))
    assertpy.assert_that(ent.parameters).is_equal_to({"/param/path/1": "param-value"})


def test_handle_should_set_account_state_to_active(
    mock_complete_project_account_onboarding_command,
    mock_uow_2,
    mock_account_repo,
    mock_projects_qs,
    mock_parameters_qs,
    message_bus_mock,
    sample_project_account_factory,
):
    # ARRANGE
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account_factory(
        error_message="Should be cleared"
    )

    # ACT
    complete_project_account_onboarding_command_handler.handle(
        command=mock_complete_project_account_onboarding_command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
        parameters_qs=mock_parameters_qs,
        account_parameters_path="/param/path",
        message_bus=message_bus_mock,
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()
    mock_account_repo.update_entity.assert_called_once()
    [_, ent] = mock_account_repo.update_entity.call_args.args

    assertpy.assert_that(ent.accountStatus).is_equal_to("Active")
    assertpy.assert_that(ent.lastOnboardingResult).is_equal_to("Succeeded")
    assertpy.assert_that(ent.lastOnboardingErrorMessage).is_none()


def test_handle_should_publish_event(
    mock_complete_project_account_onboarding_command,
    mock_uow_2,
    mock_projects_qs,
    mock_parameters_qs,
    message_bus_mock,
    sample_project_account,
):
    # ARRANGE

    # ACT
    complete_project_account_onboarding_command_handler.handle(
        command=mock_complete_project_account_onboarding_command,
        uow=mock_uow_2,
        projects_qs=mock_projects_qs,
        parameters_qs=mock_parameters_qs,
        account_parameters_path="/param/path",
        message_bus=message_bus_mock,
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once_with(
        project_account_on_boarded.ProjectAccountOnBoarded(
            projectId=sample_project_account.projectId,
            technologyId=sample_project_account.technologyId,
            awsAccountId=sample_project_account.awsAccountId,
            accountId=sample_project_account.id,
            accountType=sample_project_account.accountType,
            stage=sample_project_account.stage,
            region=sample_project_account.region,
        )
    )
