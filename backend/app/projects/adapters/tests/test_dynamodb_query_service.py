import datetime
import uuid
from typing import List, Optional

import assertpy
import pendulum
import pytest
from botocore.stub import Stubber

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.adapters.repository import dynamo_entity_config
from app.projects.domain.exceptions import repository_exception
from app.projects.domain.model import (
    enrolment,
    project,
    project_account,
    project_assignment,
    technology,
)
from app.projects.domain.model import user as user_model
from app.projects.domain.ports import enrolment_query_service
from app.projects.domain.value_objects.account_type_value_object import AccountTypeEnum
from app.shared.adapters.boto import paging_utils


@pytest.fixture()
def create_date():
    return pendulum.datetime(year=2022, month=4, day=1, hour=12)


@pytest.fixture()
def last_updated_date():
    return pendulum.datetime(year=2022, month=4, day=1, hour=13)


@pytest.fixture()
def sample_projects(create_date, last_updated_date):
    project_count = 5
    current_time = create_date
    update_time = last_updated_date
    return [
        project.Project(
            projectId=f"p{str(i)}",
            projectName="test-name",
            projectDescription="test-description",
            isActive=True,
            createDate=current_time.to_iso8601_string(),
            lastUpdateDate=update_time.to_iso8601_string(),
        )
        for i in range(project_count)
    ]


@pytest.fixture()
def sample_users():
    return [f"u{i}" for i in range(5)]


@pytest.fixture()
def sample_query_response():
    return {
        "Items": [
            {
                "PK": {"S": "USER#u0"},
                "SK": {"S": "PROJECT#p0"},
                "userId": {"S": "u0"},
                "projectId": {"S": "p0"},
                "roles": {
                    "L": [
                        {"S": project_assignment.Role.PLATFORM_USER.value},
                        {"S": project_assignment.Role.ADMIN.value},
                    ]
                },
            },
        ],
        "Count": 1,
        "ScannedCount": 1,
    }


@pytest.fixture()
def sample_batch_get_item_unprocessed_response():
    return {
        "Responses": {"test-table": []},
        "UnprocessedKeys": {
            "test-table": {
                "Keys": [
                    {
                        "PK": {"S": "PROJECT#pid"},
                        "SK": {"S": "PROJECT#pid"},
                    },
                ]
            },
        },
    }


@pytest.fixture()
def dynamodb_stub(mock_dynamodb):
    with Stubber(mock_dynamodb.meta.client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def make_fake_assignments(target_projects: List[project.Project], target_users: List[str]):
    assignments = []
    for user in target_users:
        for proj in target_projects:
            assignment = project_assignment.Assignment(
                userId=user,
                projectId=proj.projectId,
                roles=[project_assignment.Role.PLATFORM_USER, project_assignment.Role.ADMIN],
                userEmail="fake@email.com",
            )
            assignments.append(assignment)
    return assignments


@pytest.fixture
def get_mock_user():
    def _get_mock_user():
        return user_model.User(
            userId="u0",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user_model.UserADStatus.PENDING,
            userEmail="fake@email.com",
        )

    return _get_mock_user


def make_fake_project_account(
    account_type: AccountTypeEnum = AccountTypeEnum.USER,
    stage: project_account.ProjectAccountStageEnum = project_account.ProjectAccountStageEnum.DEV,
    region: Optional[str] = "us-east-1",
    technologyId: str = "uuid-abc",
    projectId="proj-123",
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
        accountStatus=project_account.ProjectAccountStatusEnum.Creating,
        technologyId=technologyId,
        stage=stage,
        region=region,
        projectId=projectId,
    )


def make_fake_technology(name: str):
    current_time = datetime.datetime.fromisoformat("2022-12-01T00:12:00+00:00")
    current_time_iso = current_time.isoformat()
    return technology.Technology(
        name=name, description="sample tech desc", createDate=current_time_iso, lastUpdateDate=current_time_iso
    )


def make_fake_enrolments(
    project_id: str, user_id: str, status: enrolment.EnrolmentStatus = enrolment.EnrolmentStatus.Pending
):
    return enrolment.Enrolment(projectId=project_id, userId=user_id, status=status)


def fill_db_with_entities(backend_app_dynamodb_table, projects=None, assignments=None, users=None):
    if not projects:
        projects = []
    for proj in projects:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"PROJECT#{proj.projectId}",
                "SK": f"PROJECT#{proj.projectId}",
                "entity": "PROJECT",
                **proj.model_dump(),
            }
        )
    if not assignments:
        assignments = []
    for assign in assignments:
        backend_app_dynamodb_table.put_item(
            Item={"PK": f"USER#{assign.userId}", "SK": f"PROJECT#{assign.projectId}", **assign.model_dump()}
        )

    if not users:
        users = []
    for _user in users:
        backend_app_dynamodb_table.put_item(
            Item={"PK": f"USER#{_user.userId}", "SK": f"USER#{_user.userId}", **_user.model_dump()}
        )


def test_can_return_all_projects_for_given_user(
    mock_dynamodb,
    sample_users,
    backend_app_dynamodb_table,
    sample_projects,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    expected_project_count = 5
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    projects, next_token, assignments = query_service.list_projects_by_user(
        user_id=fake_assignments[0].userId, page_size=10, next_token=None
    )

    # Assert
    assertpy.assert_that(projects).is_length(expected_project_count)
    assertpy.assert_that(next_token).is_none()
    for proj in sample_projects:
        assertpy.assert_that(projects).contains(proj)

    user_assignments = [
        assignment for assignment in fake_assignments if assignment.userId == fake_assignments[0].userId
    ]
    for assignment in user_assignments:
        assertpy.assert_that(assignments).contains(assignment)


def test_can_return_all_projects(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)
    expected_project_count = 5

    # Act
    projects, next_token, assignments = query_service.list_projects(user_id="u0", page_size=10, next_token=None)

    # Assert
    assertpy.assert_that(projects).is_length(expected_project_count)
    for proj in projects:
        assertpy.assert_that(sample_projects).contains(proj)

    user_assignments = [
        assignment for assignment in fake_assignments if assignment.userId == fake_assignments[0].userId
    ]
    for assignment in user_assignments:
        assertpy.assert_that(assignments).contains(assignment)


def test_list_projects_should_return_all_projects_when_table_has_many_records(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    with mock_ddb_repo:
        for i in range(10):
            new_account = make_fake_project_account(projectId=sample_projects[i % 5].projectId)
            mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
                new_account
            )
        mock_ddb_repo.commit()
    expected_project_count = 3

    # Act
    projects, next_token, assignments = query_service.list_projects(user_id="u0", page_size=3, next_token=None)

    # Assert
    assertpy.assert_that(projects).is_length(expected_project_count)
    for proj in projects:
        assertpy.assert_that(sample_projects).contains(proj)


def test_can_return_paginated_projects_for_given_user(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    expected_project_count = 3
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    projects_first_page, next_token_to_second_page, assignments = query_service.list_projects_by_user(
        user_id=fake_assignments[0].userId, page_size=2, next_token=None
    )
    projects, next_token, assignments = query_service.list_projects_by_user(
        user_id=fake_assignments[0].userId, page_size=10, next_token=next_token_to_second_page
    )

    # Assert
    assertpy.assert_that(projects).is_length(expected_project_count)
    assertpy.assert_that(next_token_to_second_page).is_not_none()
    assertpy.assert_that(next_token).is_none()
    for first_page_project in projects_first_page:
        assertpy.assert_that(projects).does_not_contain(first_page_project)


def test_can_return_empty_list_of_projects_for_unknown_user(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    projects, next_token, assignments = query_service.list_projects_by_user(
        user_id="non-existing-userid", page_size=10, next_token=None
    )

    # Assert
    assertpy.assert_that(projects).is_empty()
    assertpy.assert_that(next_token).is_none()


def test_can_return_error_on_unprocessed_keys_in_project_retrieval(
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    sample_batch_get_item_unprocessed_response,
    sample_query_response,
    dynamodb_stub,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    dynamodb_stub.add_response(method="query", service_response=sample_query_response)
    dynamodb_stub.add_response(method="batch_get_item", service_response=sample_batch_get_item_unprocessed_response)
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=dynamodb_stub.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    # Act and Assert
    with pytest.raises(repository_exception.RepositoryException):
        query_service.list_projects_by_user(user_id="u0", page_size=10, next_token=None)


@pytest.mark.parametrize("is_active", [True, False])
def test_list_projects_return_all_projects(
    is_active, mock_dynamodb, mock_ddb_repo, test_table_name, gsi_name, gsi_aws_accounts, gsi_entities
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    project_count = 5
    project_ids = [str(uuid.uuid4()) for i in range(project_count)]

    with mock_ddb_repo:
        for i in range(project_count):
            new_project = project.Project(
                projectId=project_ids[i],
                projectName="test-name",
                projectDescription="test-description",
                isActive=is_active,
                createDate=current_time,
                lastUpdateDate=current_time,
            )
            mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(new_project)
        mock_ddb_repo.commit()

    # Act
    projects, last_evaluated_key, assignments = query_service.list_projects(
        page_size=project_count * 2, next_token=None
    )

    # Assert
    assertpy.assert_that(projects).is_not_none()
    assertpy.assert_that(projects).is_length(project_count)
    assertpy.assert_that(sorted([project.projectId for project in projects])).is_equal_to(sorted(project_ids))
    assertpy.assert_that(projects[0].isActive).is_equal_to(is_active)


def test_list_projects_paging(mock_dynamodb, mock_ddb_repo, test_table_name, gsi_name, gsi_aws_accounts, gsi_entities):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    project_count = 5
    project_ids = [str(uuid.uuid4()) for i in range(project_count)]

    with mock_ddb_repo:
        for i in range(project_count):
            new_project = project.Project(
                projectId=project_ids[i],
                projectName="test-name",
                projectDescription="test-description",
                isActive=True,
                createDate=current_time,
                lastUpdateDate=current_time,
            )
            mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(new_project)
        mock_ddb_repo.commit()

    # Act & Assert
    last_evaluated_key = None
    for i in range(project_count):
        projects, last_evaluated_key, assignments = query_service.list_projects(
            page_size=1, next_token=last_evaluated_key
        )
        assertpy.assert_that(projects).is_not_none()
        assertpy.assert_that(projects).is_length(1)
        assertpy.assert_that(projects[0].projectId).is_in(*project_ids)


# for bw compatibility also testing when region is None.
@pytest.mark.parametrize("region,page_size", [("us-east-1", 1), ("us-east-1", None), (None, None)])
def test_can_list_project_accounts(
    mock_dynamodb,
    sample_projects,
    region,
    page_size,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
        default_page_size=page_size,
    )
    account_count = 3
    expected_accounts = []
    sample_project = sample_projects.pop()

    with mock_ddb_repo:
        for _ in range(account_count):
            new_account = make_fake_project_account(region=region, projectId=sample_project.projectId)
            expected_accounts.append(new_account)
            mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
                new_account
            )
        mock_ddb_repo.commit()

    # Act
    project_accounts = query_service.list_project_accounts(project_id=sample_project.projectId)

    # Assert
    assertpy.assert_that(project_accounts).contains_only(*expected_accounts)


def test_can_list_project_accounts_filtered_by_account_type(
    mock_dynamodb,
    sample_projects,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    sample_project = sample_projects.pop()
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_user_account = make_fake_project_account(
        account_type=AccountTypeEnum.USER, projectId=sample_project.projectId
    )
    sample_toolchain_account = make_fake_project_account(
        account_type=AccountTypeEnum.TOOLCHAIN, projectId=sample_project.projectId
    )

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_user_account
        )
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_toolchain_account
        )
        mock_ddb_repo.commit()

    # Act
    workbench_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId, account_type=dynamodb_query_service.AccountType.USER.value
    )
    toolchain_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId, account_type=dynamodb_query_service.AccountType.TOOLCHAIN.value
    )
    unknown_accounts = query_service.list_project_accounts(project_id=sample_project.projectId, account_type="unknown")

    # Assert
    assertpy.assert_that(workbench_accounts).contains_only(sample_user_account)
    assertpy.assert_that(toolchain_accounts).contains_only(sample_toolchain_account)
    assertpy.assert_that(unknown_accounts).is_empty()


def test_can_list_project_accounts_filtered_by_stage(
    mock_dynamodb,
    sample_projects,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    sample_project = sample_projects.pop()
    sample_dev_account = make_fake_project_account(projectId=sample_project.projectId)
    sample_qa_account = make_fake_project_account(
        stage=project_account.ProjectAccountStageEnum.QA, projectId=sample_project.projectId
    )

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_dev_account
        )
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_qa_account
        )
        mock_ddb_repo.commit()

    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )

    # Act
    dev_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId, stage=sample_dev_account.stage
    )
    qa_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId, stage=sample_qa_account.stage
    )
    unknown_accounts = query_service.list_project_accounts(project_id=sample_project.projectId, stage="unknown")

    # Assert
    assertpy.assert_that(dev_accounts).contains_only(sample_dev_account)
    assertpy.assert_that(qa_accounts).contains_only(sample_qa_account)
    assertpy.assert_that(unknown_accounts).is_empty()


def test_can_list_project_accounts_filtered_by_stage_and_account_type(
    mock_dynamodb,
    sample_projects,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    sample_project = sample_projects.pop()
    sample_tool_dev_account = make_fake_project_account(
        account_type=AccountTypeEnum.TOOLCHAIN,
        stage=project_account.ProjectAccountStageEnum.DEV,
        projectId=sample_project.projectId,
    )
    sample_user_qa_account = make_fake_project_account(
        account_type=AccountTypeEnum.USER,
        stage=project_account.ProjectAccountStageEnum.QA,
        projectId=sample_project.projectId,
    )

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_tool_dev_account
        )
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_user_qa_account
        )
        mock_ddb_repo.commit()

    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )

    # Act
    tool_dev_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId,
        account_type=sample_tool_dev_account.accountType,
        stage=sample_tool_dev_account.stage,
    )
    qa_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId,
        account_type=sample_user_qa_account.accountType,
        stage=sample_user_qa_account.stage,
    )
    unknown_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId,
        account_type=sample_user_qa_account.accountType,
        stage=sample_tool_dev_account.stage,
    )

    # Assert
    assertpy.assert_that(tool_dev_accounts).contains_only(sample_tool_dev_account)
    assertpy.assert_that(qa_accounts).contains_only(sample_user_qa_account)
    assertpy.assert_that(unknown_accounts).is_empty()


def test_can_list_project_accounts_filtered_by_technology_id(
    mock_dynamodb,
    sample_projects,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_project = sample_projects.pop()
    sample_tech_123_account = make_fake_project_account(technologyId="tech-123", projectId=sample_project.projectId)
    sample_tech_000_account = make_fake_project_account(technologyId="tech-000", projectId=sample_project.projectId)

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_tech_123_account
        )
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_tech_000_account
        )
        mock_ddb_repo.commit()

    # Act
    workbench_accounts = query_service.list_project_accounts(
        project_id=sample_project.projectId,
        account_type=dynamodb_query_service.AccountType.USER.value,
        technology_id="tech-000",
    )

    # Assert
    assertpy.assert_that(workbench_accounts).contains_only(sample_tech_000_account)


def test_get_project_account_by_id_if_exists_should_return(
    mock_dynamodb,
    sample_projects,
    mock_ddb_repo,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    sample_project = sample_projects.pop()
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_user_account = make_fake_project_account(
        account_type=AccountTypeEnum.USER, projectId=sample_project.projectId
    )

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            sample_user_account
        )
        mock_ddb_repo.commit()

    # Act
    workbench_account = query_service.get_project_account_by_id(
        project_id=sample_project.projectId, account_id=sample_user_account.id
    )

    # Assert
    assertpy.assert_that(workbench_account).is_equal_to(sample_user_account)


def test_get_project_by_id_should_return_when_exists(
    mock_dynamodb, mock_ddb_repo, test_table_name, gsi_name, gsi_aws_accounts, gsi_entities
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    project_id = str(uuid.uuid4())

    with mock_ddb_repo:
        new_project = project.Project(
            projectId=project_id,
            projectName="test-name",
            projectDescription="test-description",
            isActive=True,
            createDate=current_time,
            lastUpdateDate=current_time,
        )
        mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(new_project)
        mock_ddb_repo.commit()

    # Act
    projects = query_service.get_project_by_id(id=project_id)

    # Assert
    assertpy.assert_that(projects).is_not_none()


def test_get_project_by_id_should_return_none_when_does_not_exist(
    mock_dynamodb, test_table_name, gsi_name, gsi_aws_accounts, gsi_entities
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    project_id = str(uuid.uuid4())

    # Act
    projects = query_service.get_project_by_id(id=project_id)

    # Assert
    assertpy.assert_that(projects).is_none()


def test_list_users_by_project_should_return_project_assignments(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    expected_assignment_count = 5
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    assignments = query_service.list_users_by_project(
        project_id="p1",
    )

    # Assert
    assertpy.assert_that(assignments).is_length(expected_assignment_count)
    user_assignments = [assignment for assignment in fake_assignments if assignment.projectId == "p1"]
    for assignment in user_assignments:
        assertpy.assert_that(assignments).contains(assignment)


def test_list_users_by_project_should_return_all_assignments_when_paged(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
        default_page_size=3,
    )
    expected_assignment_count = 5
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    assignments = query_service.list_users_by_project(
        project_id="p1",
    )

    # Assert
    assertpy.assert_that(assignments).is_length(expected_assignment_count)

    user_assignments = [assignment for assignment in fake_assignments if assignment.projectId == "p1"]
    for assignment in user_assignments:
        assertpy.assert_that(assignments).contains(assignment)


def test_list_users_by_project_paged_should_return_assignments_page(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
        default_page_size=3,
    )
    expected_assignment_count = 2
    fake_assignments = make_fake_assignments(sample_projects, sample_users)
    fill_db_with_entities(backend_app_dynamodb_table, sample_projects, fake_assignments)

    # Act
    response = query_service.list_users_by_project_paged(
        project_id="p1", page=paging_utils.PageInfo(page_size=expected_assignment_count)
    )
    response_page_2 = query_service.list_users_by_project_paged(
        project_id="p1", page=paging_utils.PageInfo(page_size=expected_assignment_count, page_token=response.page_token)
    )

    # Assert
    assertpy.assert_that(response.items).is_length(expected_assignment_count)
    assertpy.assert_that(response_page_2.items).is_length(expected_assignment_count)

    assertpy.assert_that(response.items).contains_only(
        project_assignment.Assignment(
            userId="u0",
            projectId="p1",
            roles=[project_assignment.Role.PLATFORM_USER, project_assignment.Role.ADMIN],
            userEmail="fake@email.com",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user_model.UserADStatus.UNKNOWN,
            lastUpdateDate=None,
        ),
        project_assignment.Assignment(
            userId="u1",
            projectId="p1",
            roles=[project_assignment.Role.PLATFORM_USER, project_assignment.Role.ADMIN],
            userEmail="fake@email.com",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user_model.UserADStatus.UNKNOWN,
            lastUpdateDate=None,
        ),
    )
    assertpy.assert_that(response_page_2.items).contains_only(
        project_assignment.Assignment(
            userId="u2",
            projectId="p1",
            roles=[project_assignment.Role.PLATFORM_USER, project_assignment.Role.ADMIN],
            userEmail="fake@email.com",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user_model.UserADStatus.UNKNOWN,
            lastUpdateDate=None,
        ),
        project_assignment.Assignment(
            userId="u3",
            projectId="p1",
            roles=[project_assignment.Role.PLATFORM_USER, project_assignment.Role.ADMIN],
            userEmail="fake@email.com",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user_model.UserADStatus.UNKNOWN,
            lastUpdateDate=None,
        ),
    )


def test_can_list_technologies_for_project(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBTechnologiesQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
    )

    sample_project = sample_projects.pop()
    sample_techs = [make_fake_technology(str(i)) for i in range(2)]

    for tech in sample_techs:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.TECHNOLOGY}#{tech.id}",
                **tech.model_dump(),
            }
        )

    # Act
    expected_techs = query_service.list_technologies(project_id=sample_project.projectId, page_size=10)

    # Assert
    assertpy.assert_that(sample_techs).contains_only(*expected_techs)


def test_can_return_empty_list_technologies_for_project(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBTechnologiesQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
    )

    sample_project = sample_projects.pop()

    # Act
    expected_techs = query_service.list_technologies(project_id=sample_project.projectId, page_size=10)

    # Assert
    assertpy.assert_that(expected_techs).is_empty()


def test_can_list_project_accounts_by_aws_account(
    mock_dynamodb,
    backend_app_dynamodb_table,
    sample_projects,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )

    sample_project = sample_projects.pop()
    sample_pa_accounts = [make_fake_project_account() for i in range(2)]

    for pa in sample_pa_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )
    sample_pa = sample_pa_accounts.pop()

    # Act
    results = query_service.list_project_accounts_by_aws_account(sample_pa.awsAccountId)

    # Assert
    assertpy.assert_that(results).contains_only(sample_pa)


def test_list_all_accounts_all_types_all_projects(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_project = sample_projects.pop()
    sample_pa_accounts = [make_fake_project_account() for i in range(5)]

    for pa in sample_pa_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )

    # Act
    project_accounts, last_evaluated_key = query_service.list_all_accounts(page_size=10, next_token=None)

    # Assert
    assertpy.assert_that(sample_pa_accounts).contains_only(*project_accounts)


def test_list_all_accounts_all_types_all_projects_paging(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_project = sample_projects.pop()
    sample_pa_accounts = [make_fake_project_account() for i in range(5)]

    for pa in sample_pa_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )

    # Act
    projects_first_page, next_token_to_second_page = query_service.list_all_accounts(page_size=1, next_token=None)

    project_accounts, last_evaluated_key = query_service.list_all_accounts(
        page_size=10, next_token=next_token_to_second_page
    )

    # Assert
    assertpy.assert_that(next_token_to_second_page).is_not_none()
    assertpy.assert_that(sample_pa_accounts).contains(*projects_first_page)
    assertpy.assert_that(last_evaluated_key).is_none()
    assertpy.assert_that(sample_pa_accounts).contains(*project_accounts)


def test_list_all_accounts_specific_types_all_projects(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_project = sample_projects.pop()
    sample_pa_user_accounts = [make_fake_project_account() for i in range(1)]
    sample_pa_tool_accounts = [make_fake_project_account(account_type=AccountTypeEnum.TOOLCHAIN) for i in range(1)]

    for pa in sample_pa_user_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )
    for pa in sample_pa_tool_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )

    # Act
    project_accounts, last_evaluated_key = query_service.list_all_accounts(
        page_size=10, next_token=None, account_type=AccountTypeEnum.TOOLCHAIN
    )

    # Assert
    assertpy.assert_that(sample_pa_tool_accounts).contains_only(*project_accounts)


def test_list_all_accounts_specific_types_all_projects_paging(
    mock_dynamodb,
    sample_projects,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    sample_project = sample_projects.pop()
    sample_pa_user_accounts = [make_fake_project_account() for i in range(5)]
    sample_pa_tool_accounts = [make_fake_project_account(account_type=AccountTypeEnum.TOOLCHAIN) for i in range(5)]

    for pa in sample_pa_user_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )
    for pa in sample_pa_tool_accounts:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT}#{pa.id}",
                **pa.model_dump(),
            }
        )

    # Act
    projects_first_page, next_token_to_second_page = query_service.list_all_accounts(
        page_size=6, next_token=None, account_type=AccountTypeEnum.TOOLCHAIN
    )

    project_accounts, last_evaluated_key = query_service.list_all_accounts(
        page_size=10, next_token=next_token_to_second_page, account_type=AccountTypeEnum.TOOLCHAIN
    )

    # Assert
    assertpy.assert_that(next_token_to_second_page).is_not_none()
    assertpy.assert_that(last_evaluated_key).is_none()
    all_results = projects_first_page + project_accounts
    assertpy.assert_that(all_results).is_not_empty()
    assertpy.assert_that(sample_pa_tool_accounts).contains(*all_results)


def test_enrolment_query_service_can_return_enrolment_for_userid_and_project_id(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    sample_project = sample_projects.pop()
    sample_user = sample_users.pop()
    sample_enrolment = make_fake_enrolments(sample_project.projectId, sample_user)

    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
            "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
            **sample_enrolment.model_dump(),
        }
    )

    # Act
    queried_enrolment = query_service.get_enrolment_for_user(project_id=sample_project.projectId, user_id=sample_user)

    # Assert
    assertpy.assert_that(sample_enrolment).is_equal_to(queried_enrolment)


def test_enrolment_query_service_can_return_none_for_userid_without_enrolment_in_project_id(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    sample_project = sample_projects.pop()
    sample_user = sample_users.pop()
    sample_enrolment = make_fake_enrolments(sample_project.projectId, sample_user)

    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
            "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
            **sample_enrolment.model_dump(),
        }
    )

    # Act
    queried_enrolment = query_service.get_enrolment_for_user(project_id=sample_project.projectId, user_id="evil_user")

    # Assert
    assertpy.assert_that(queried_enrolment).is_none()


def test_enrolment_query_service_can_return_none_for_invalid_project_id(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    sample_project = sample_projects.pop()
    sample_user = sample_users.pop()
    sample_enrolment = make_fake_enrolments(sample_project.projectId, sample_user)

    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_project.projectId}",
            "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
            **sample_enrolment.model_dump(),
        }
    )

    # Act
    queried_enrolment = query_service.get_enrolment_for_user(project_id="evil_project_id", user_id=sample_user)

    # Assert
    assertpy.assert_that(queried_enrolment).is_none()


def test_get_enrolment_by_id(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    sample_enrolment = make_fake_enrolments(sample_projects[0].projectId, sample_users[0])

    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_projects[0].projectId}",
            "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
            **sample_enrolment.model_dump(),
        }
    )

    # Act
    queried_enrolment = query_service.get_enrolment_by_id(
        enrolment_id=sample_enrolment.id, project_id=sample_projects[0].projectId
    )

    # Assert
    assertpy.assert_that(queried_enrolment).is_equal_to(sample_enrolment)


def test_list_enrolments_by_project(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    for proj in sample_projects:
        for user in sample_users:
            sample_enrolment = make_fake_enrolments(proj.projectId, user)
            backend_app_dynamodb_table.put_item(
                Item={
                    "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{proj.projectId}",
                    "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
                    **sample_enrolment.model_dump(),
                }
            )

    # Act
    queried_enrolment, token = query_service.list_enrolments_by_project(
        project_id=sample_projects[0].projectId, page_size=10, next_token=None
    )

    # Assert
    for enrolment_item in queried_enrolment:
        assertpy.assert_that(enrolment_item.projectId).is_equal_to(sample_projects[0].projectId)


def test_list_enrolments_by_user_id(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrange
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    user = sample_users[0]

    for proj in sample_projects:
        for user in sample_users:
            sample_enrolment = make_fake_enrolments(proj.projectId, user)
            backend_app_dynamodb_table.put_item(
                Item={
                    "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{proj.projectId}",
                    "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
                    "QPK": f"{dynamo_entity_config.DBPrefix.USER}#{user}",
                    **sample_enrolment.model_dump(),
                }
            )

    # Act
    queried_enrolments, token = query_service.list_enrolments_by_user(
        user_id=user, page_size=10, next_token=None, status=enrolment.EnrolmentStatus.Pending, project_id="p0"
    )

    # Assert
    for enrolment_item in queried_enrolments:
        assertpy.assert_that(enrolment_item.userId).is_equal_to(user)
        assertpy.assert_that(enrolment_item.projectId).is_equal_to("p0")


def test_list_enrolments_by_project_should_filter_by_status(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    test_table_name,
    gsi_qpk,
    gsi_qsk,
):
    # Arrangegsi_qsk
    query_service: enrolment_query_service.EnrolmentQueryService = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=test_table_name, dynamodb_client=mock_dynamodb.meta.client, gsi_qpk=gsi_qpk, gsi_qsk=gsi_qsk
    )

    for proj in sample_projects:
        for user in sample_users:
            sample_enrolment = make_fake_enrolments(proj.projectId, user)
            backend_app_dynamodb_table.put_item(
                Item={
                    "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{proj.projectId}",
                    "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{sample_enrolment.id}",
                    "QSK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#Approved#{sample_enrolment.id}",
                    **sample_enrolment.model_dump(),
                }
            )

    pending_enrolment = make_fake_enrolments(sample_projects[0].projectId, "UID-123", enrolment.EnrolmentStatus.Pending)
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{sample_projects[0].projectId}",
            "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{pending_enrolment.id}",
            "QSK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#Pending#{pending_enrolment.id}",
            **pending_enrolment.model_dump(),
        }
    )

    # Act
    queried_enrolments, token = query_service.list_enrolments_by_project(
        project_id=sample_projects[0].projectId, page_size=50, next_token=None, status=enrolment.EnrolmentStatus.Pending
    )

    # Assert
    assertpy.assert_that(queried_enrolments).is_length(1)
    assertpy.assert_that(queried_enrolments[0]).is_equal_to(pending_enrolment)


def test_get_user_returns_user(
    mock_dynamodb,
    sample_projects,
    sample_users,
    backend_app_dynamodb_table,
    get_mock_user,
    test_table_name,
    gsi_name,
    gsi_aws_accounts,
    gsi_entities,
):
    # Arrange
    query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=gsi_name,
        gsi_aws_accounts=gsi_aws_accounts,
        gsi_entities=gsi_entities,
    )
    fake_user = get_mock_user()
    fill_db_with_entities(backend_app_dynamodb_table, users=[fake_user])

    # Act
    user_entity = query_service.get_user(user_id="u0")

    # Assert
    assertpy.assert_that(user_entity).is_equal_to(fake_user)
