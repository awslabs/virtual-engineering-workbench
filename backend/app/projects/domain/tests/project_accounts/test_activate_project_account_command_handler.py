import datetime
import uuid

import assertpy

from app.projects.domain.command_handlers.project_accounts import activate_project_account_command_handler
from app.projects.domain.commands.project_accounts import activate_project_account_command
from app.projects.domain.model import project_account
from app.projects.domain.value_objects import (
    account_id_value_object,
    account_status_value_object,
    project_id_value_object,
)


def make_fake_project_account(
    account_type: str = "USER",
    stage: str = "dev",
    status: project_account.ProjectAccountStatusEnum = project_account.ProjectAccountStatusEnum.Creating,
):
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return project_account.ProjectAccount(
        awsAccountId=str(uuid.uuid4()),
        accountType=account_type,
        accountName="fake",
        accountDescription="fake desc",
        createDate=current_time,
        lastUpdateDate=update_time,
        accountStatus=status,
        technologyId="uuid-abc",
        stage=stage,
        projectId="proj-123",
    )


def test_can_activate_inactive_project_account(handler_dependencies, mock_uow_2, mock_account_repo):
    # Arrange
    account = make_fake_project_account(status=project_account.ProjectAccountStatusEnum.Inactive)
    command = activate_project_account_command.ActivateProjectAccountCommand(
        account_id=account_id_value_object.from_str(account.id),
        account_status=account_status_value_object.from_value_str("Active"),
        project_id=project_id_value_object.from_str("fake_project_id"),
    )
    (_, projects_query_service_mock, _) = handler_dependencies
    projects_query_service_mock.list_project_accounts.return_value = [account]

    # Act
    activate_project_account_command_handler.handle_activate_project_account_command(
        cmd=command, unit_of_work=mock_uow_2, projects_qry_srv=projects_query_service_mock
    )

    # Assert
    mock_uow_2.commit.assert_called_once()
    (key, ent) = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(key).is_equal_to(
        {
            "projectId": "fake_project_id",
            "id": account.id,
        }
    )
    assertpy.assert_that(ent.accountStatus).is_equal_to("Active")
