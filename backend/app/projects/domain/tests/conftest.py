import logging
from unittest import mock

import pytest
from freezegun import freeze_time

from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
    fail_project_account_onboarding_command,
    on_board_project_account_command,
    reonboard_project_account_command,
)
from app.projects.domain.model import (
    enrolment,
    project,
    project_account,
    project_assignment,
    technology,
    user,
)
from app.projects.domain.ports import projects_query_service
from app.projects.domain.value_objects import (
    account_description_value_object,
    account_error_message_value_object,
    account_id_value_object,
    account_name_value_object,
    account_technology_id_value_object,
    account_type_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
)
from app.shared.adapters.boto import (
    parameter_service_v2,
    resource_access_management_service,
)
from app.shared.adapters.message_bus import message_bus as msg_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work as unit_of_work_v2


@pytest.fixture
def handler_dependencies(message_bus_mock):
    uow_mock = mock.MagicMock()
    projects_query_service_mock = mock.create_autospec(spec=projects_query_service.ProjectsQueryService, instance=True)
    return uow_mock, projects_query_service_mock, message_bus_mock


@pytest.fixture()
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture
def message_bus_mock():
    yield mock.create_autospec(spec=msg_bus.MessageBus, instance=True)


@pytest.fixture
def mock_account_repo():
    yield mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)


@pytest.fixture
def mock_projects_repo():
    yield mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)


@pytest.fixture
def mock_assignments_repo():
    yield mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)


@pytest.fixture
def mock_enrolments_repo():
    yield mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)


@pytest.fixture
def mock_technologies_repo():
    yield mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)


@pytest.fixture
def mock_users_repo():
    m = mock.create_autospec(spec=unit_of_work_v2.GenericRepository, instance=True)
    m.get.return_value = None
    yield m


@pytest.fixture
def mock_commit_context():
    yield []


@pytest.fixture
def mock_uow_2(mock_uow_2_factory):
    return mock_uow_2_factory(context_aware=False)


@pytest.fixture
def mock_uow_2_ca(mock_uow_2_factory):
    return mock_uow_2_factory(context_aware=True)


@pytest.fixture
def mock_uow_2_factory(
    mock_account_repo,
    mock_projects_repo,
    mock_assignments_repo,
    mock_enrolments_repo,
    mock_commit_context,
    mock_users_repo,
    mock_technologies_repo,
):
    def __factory(context_aware=False):
        repos = {
            project_account.ProjectAccount: mock_account_repo,
            project.Project: mock_projects_repo,
            project_assignment.Assignment: mock_assignments_repo,
            enrolment.Enrolment: mock_enrolments_repo,
            user.User: mock_users_repo,
            technology.Technology: mock_technologies_repo,
        }

        uow = mock.create_autospec(spec=unit_of_work_v2.UnitOfWork, instance=True)

        def __get_repo(_, repo_type):
            return repos[repo_type]

        uow.get_repository.side_effect = __get_repo

        def __commit():
            mock_commit_context.append(
                {
                    project_assignment.Assignment: {
                        "remove": mock_assignments_repo.remove.call_args_list,
                    },
                    enrolment.Enrolment: {
                        "remove": mock_enrolments_repo.remove.call_args_list,
                    },
                }
            )
            mock_assignments_repo.reset_mock()
            mock_enrolments_repo.reset_mock()

        if context_aware:
            uow.commit.side_effect = __commit

        return uow

    return __factory


@pytest.fixture
def mock_projects_qs(sample_project, sample_project_account):
    mock_projects_qs = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    mock_projects_qs.get_project_by_id.return_value = sample_project
    mock_projects_qs.get_project_account_by_id.return_value = sample_project_account
    return mock_projects_qs


@pytest.fixture
def mock_parameters_qs():
    mock_parameters_qs = mock.create_autospec(spec=parameter_service_v2.ParameterService)
    return mock_parameters_qs


@pytest.fixture
def mock_on_board_project_account_command():
    return on_board_project_account_command.OnBoardProjectAccountCommand(
        account_id=aws_account_id_value_object.from_str("001234567890"),
        account_type=account_type_value_object.from_str("USER"),
        account_name=account_name_value_object.from_str("Test Account"),
        account_description=account_description_value_object.from_str("Test Account Description"),
        project_id=project_id_value_object.from_str("123"),
        stage=project_account.ProjectAccountStageEnum.DEV,
        technology=account_technology_id_value_object.from_str("321"),
        region=region_value_object.from_str("us-east-1"),
    )


@pytest.fixture
def mock_reonboard_project_account_command():
    return reonboard_project_account_command.ReonboardProjectAccountCommand(
        account_id=account_id_value_object.from_str("321"),
        project_id=project_id_value_object.from_str("123"),
    )


@pytest.fixture
def on_board_project_account_different_region_command():
    return on_board_project_account_command.OnBoardProjectAccountCommand(
        account_id=aws_account_id_value_object.from_str("001234567890"),
        account_type=account_type_value_object.from_str("USER"),
        account_name=account_name_value_object.from_str("Test Account"),
        account_description=account_description_value_object.from_str("Test Account Description"),
        project_id=project_id_value_object.from_str("123"),
        stage=project_account.ProjectAccountStageEnum.DEV,
        technology=account_technology_id_value_object.from_str("321"),
        region=region_value_object.from_str("eu-west-3"),
    )


@pytest.fixture
def mock_complete_project_account_onboarding_command():
    return complete_project_account_onboarding_command.CompleteProjectAccountOnboarding(
        project_id=project_id_value_object.from_str("123"),
        account_id=account_id_value_object.from_str("321"),
    )


@pytest.fixture
def mock_fail_project_account_onboarding_command():
    return fail_project_account_onboarding_command.FailProjectAccountOnboarding(
        project_id=project_id_value_object.from_str("123"),
        account_id=account_id_value_object.from_str("321"),
        error=account_error_message_value_object.from_str(error="Test", cause="Test cause"),
    )


@pytest.fixture
def sample_project():
    return project.Project(
        projectId="123",
        projectName="Test",
        projectDescription=None,
        isActive=True,
        createDate=None,
        lastUpdateDate=None,
    )


@pytest.fixture
def user_sample_assignment():
    def _inner(user_id: str = "U0"):
        return project_assignment.Assignment(
            userId=user_id,
            projectId="123",
            roles=[project_assignment.Role.PLATFORM_USER],
        )

    return _inner


@pytest.fixture
def admin_sample_assignment():
    return project_assignment.Assignment(userId="U0", projectId="123", roles=[project_assignment.Role.ADMIN])


@pytest.fixture
def owner_sample_assignment():
    return project_assignment.Assignment(userId="U0", projectId="333", roles=[project_assignment.Role.PROGRAM_OWNER])


@pytest.fixture
def both_sample_assignment():
    def _inner(user_id: str = "U0"):
        return project_assignment.Assignment(
            userId=user_id,
            projectId="123",
            roles=[
                project_assignment.Role.PLATFORM_USER,
                project_assignment.Role.ADMIN,
            ],
        )

    return _inner


@pytest.fixture
def sample_project_account(sample_project_account_factory):
    return sample_project_account_factory()


@pytest.fixture
def sample_project_account_factory():
    def __inner(account_status=None, error_message: str | None = None):
        return project_account.ProjectAccount(
            awsAccountId="123",
            accountType="USER",
            stage="dev",
            region="us-east-1",
            technologyId="tech-abcdf",
            projectId="proj-123",
            accountStatus=account_status,
            lastOnboardingErrorMessage=error_message,
        )

    return __inner


@pytest.fixture
def sample_technologies():
    return [technology.Technology(name="tech-1", id="tech-abcde")]


@pytest.fixture
def mocked_ram_srv():
    m = mock.create_autospec(spec=resource_access_management_service.ResourceAccessManagementService)
    m.get_resource_shares.return_value = []
    return m


@pytest.fixture
def mocked_ram_srv_tag():
    return "tag-name"


@pytest.fixture
def ecs_task_error(ecs_task_error_factory):
    return ecs_task_error_factory(
        error_msg="Unexpected EC2 error while attempting to Create Network Interface in subnet '': InsufficientFreeAddressesInSubnet"
    )


@pytest.fixture
def ecs_task_error_factory():
    def __inner(error_msg: str = ""):
        return {
            "Attachments": [],
            "Attributes": [],
            "AvailabilityZone": "us-east-1a",
            "ClusterArn": "-",
            "Connectivity": "CONNECTED",
            "ConnectivityAt": 1738758758191,
            "Containers": [],
            "Cpu": "-",
            "CreatedAt": 1738758754707,
            "DesiredStatus": "STOPPED",
            "EnableExecuteCommand": False,
            "EphemeralStorage": {"SizeInGiB": 20},
            "ExecutionStoppedAt": 1738758786291,
            "Group": "-",
            "InferenceAccelerators": [],
            "LastStatus": "STOPPED",
            "LaunchType": "FARGATE",
            "Memory": "8192",
            "Overrides": {
                "ContainerOverrides": [],
                "InferenceAcceleratorOverrides": [],
            },
            "PlatformVersion": "1.4.0",
            "PullStartedAt": 1738758764723,
            "PullStoppedAt": 1738758779767,
            "StartedAt": 1738758785453,
            "StartedBy": "AWS Step Functions",
            "StopCode": "TaskFailedToStart",
            "StoppedAt": 1738758810537,
            "StoppedReason": error_msg,
            "StoppingAt": 1738758796329,
            "Tags": [],
            "TaskArn": "-",
            "TaskDefinitionArn": "-",
            "Version": 5,
        }

    return __inner


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00"):
        yield
