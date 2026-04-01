import assertpy

from app.projects.domain.command_handlers.project_accounts import (
    reonboard_project_account_command_handler as command_handler,
)
from app.projects.domain.events.project_accounts import project_account_on_boarding_restarted
from app.projects.domain.model import project_account
from app.projects.domain.value_objects import account_type_value_object


def test_reonboard_project_account_should_publish_event(
    mock_reonboard_project_account_command, sample_project, handler_dependencies, mock_uow_2, mock_account_repo
):
    # ARRANGE
    cmd = mock_reonboard_project_account_command
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    mock_account_repo.get.return_value = project_account.ProjectAccount(
        id="321",
        awsAccountId="001234567890",
        accountType=account_type_value_object.AccountTypeEnum.USER,
        accountName="test",
        accountDescription="test",
        stage="dev",
        accountStatus="Failed",
        technologyId="tech-123",
        region="eu-west-1",
        projectId="proj-123",
    )  # type: ignore

    # ACT
    command_handler.handle(
        command=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        web_application_account_id="001234567890",
        web_application_environment="dev",
        web_application_region="us-east-1",
        image_service_account_id="001234567890",
        catalog_service_account_id="123456789012",
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once()
    event_obj = message_bus_mock.publish.call_args.args[0]

    assertpy.assert_that(event_obj).is_instance_of(
        project_account_on_boarding_restarted.ProjectAccountOnBoardingRestarted
    )
    event_obj_dict = event_obj.model_dump(by_alias=True)

    assertpy.assert_that(event_obj_dict).contains_entry({"accountId": "001234567890"})
    assertpy.assert_that(event_obj_dict).contains_entry({"accountType": "workbench-user"})
    assertpy.assert_that(event_obj_dict).contains_entry({"accountEnvironment": "dev"})
    assertpy.assert_that(event_obj_dict).contains_entry({"programId": "123"})
    assertpy.assert_that(event_obj_dict).contains_entry({"programName": "Test"})
    assertpy.assert_that(event_obj_dict).contains_entry({"region": "eu-west-1"})
    assertpy.assert_that(event_obj_dict).contains_entry(
        {
            "variables": {
                "account": "001234567890",
                "environment": "dev",
                "region": "eu-west-1",
                "web-application-account-id": "001234567890",
                "web-application-region": "us-east-1",
                "image-service-account": "001234567890",
                "catalog-service-account": "123456789012",
            }
        }
    )


def test_can_onboard_new_account_to_existing_project(
    mock_reonboard_project_account_command, sample_project, handler_dependencies, mock_uow_2, mock_account_repo
):
    # ARRANGE
    cmd = mock_reonboard_project_account_command
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    mock_account_repo.get.return_value = project_account.ProjectAccount(
        id="321",
        awsAccountId="001234567890",
        accountType=account_type_value_object.AccountTypeEnum.USER,
        accountName="test",
        accountDescription="test",
        stage="dev",
        accountStatus="Failed",
        technologyId="tech-123",
        region="eu-west-1",
        projectId="proj-123",
    )  # type: ignore

    # ACT
    command_handler.handle(
        command=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        web_application_account_id="001234567890",
        web_application_environment="dev",
        web_application_region="us-east-1",
        image_service_account_id="001234567890",
        catalog_service_account_id="123456789012",
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()
    (key, ent) = mock_account_repo.update_entity.call_args.args
    assertpy.assert_that(key.model_dump()).is_equal_to(
        {
            "projectId": "123",
            "id": "321",
        }
    )
    assertpy.assert_that(ent.accountStatus).is_equal_to("OnBoarding")
