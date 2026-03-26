import datetime
import logging
import uuid
from enum import Enum
from unittest import mock

import boto3
import moto
import pytest

from app.projects.adapters.repository import dynamo_entity_config
from app.projects.adapters.services import aws_dns_service
from app.projects.domain.model import (
    enrolment,
    project,
    project_account,
    project_assignment,
    technology,
    user,
)
from app.projects.domain.value_objects.account_type_value_object import AccountTypeEnum
from app.shared.adapters.boto.boto_provider import BotoProvider, BotoProviderOptions
from app.shared.adapters.boto.dict_context_provider import DictCtxProvider
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

TEST_REGION = "us-east-1"
TEST_TABLE_NAME = "test-table"
GSI_NAME = "gsi_inverted_primary_key"
GSI_AWS_ACCOUNTS = "gsi_aws_accounts"
GSI_ENTITIES = "gsi_entities"
GSI_QPK = "qpk_query_key"
GSI_QSK = "qsk_query_key"


class GlobalVariables(Enum):
    COMMENT: str = "comment"
    DNS_NAME: str = "example.com"
    VPC_ID: str = "vpc-0a1b2c3d4e5f67890"
    VPC_REGION: str = "us-east-1"
    ZONE_ID: str = "Z1ABCDEFGHIJK2"


@pytest.fixture(scope="function")
def required_env_vars(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture()
def test_table_name():
    return TEST_TABLE_NAME


@pytest.fixture()
def gsi_name():
    return GSI_NAME


@pytest.fixture()
def gsi_aws_accounts():
    return GSI_AWS_ACCOUNTS


@pytest.fixture()
def gsi_entities():
    return GSI_ENTITIES


@pytest.fixture()
def gsi_qpk():
    return GSI_QPK


@pytest.fixture()
def gsi_qsk():
    return GSI_QSK


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=TEST_REGION)


@pytest.fixture(autouse=True)
def mock_ec2():
    with moto.mock_aws():
        yield boto3.client(
            "ec2",
            region_name=TEST_REGION,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_route53():
    with moto.mock_aws():
        yield boto3.client(
            "route53",
            region_name=TEST_REGION,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name="eu-central-1")


@pytest.fixture(autouse=True)
def backend_app_dynamodb_table(mock_dynamodb):
    table = mock_dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "awsAccountId", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
            {"AttributeName": "QPK", "AttributeType": "S"},
            {"AttributeName": "QSK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI_NAME,
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_AWS_ACCOUNTS,
                "KeySchema": [{"AttributeName": "awsAccountId", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_ENTITIES,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_QPK,
                "KeySchema": [
                    {"AttributeName": "QPK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_QSK,
                "KeySchema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "QSK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    table.meta.client.get_waiter("table_exists").wait(TableName=TEST_TABLE_NAME)
    return table


@pytest.fixture()
def mock_aws_dns_service(mock_route53_provider):
    return aws_dns_service.AWSDNSService(route53_provider=mock_route53_provider)


@pytest.fixture()
def mock_logger():
    mock_logger = mock.create_autospec(spec=logging.Logger)
    return mock_logger


@pytest.fixture()
def mock_provider(mock_logger, required_env_vars):
    ctx = DictCtxProvider()
    return BotoProvider(
        ctx,
        mock_logger,
        default_options=BotoProviderOptions(
            aws_role_name="TestRole",
            aws_session_name="TestSession",
        ),
    )


@pytest.fixture()
def mock_route53_provider(mock_provider):
    return mock_provider.client("route53")


@pytest.fixture()
def mock_ddb_repo(mock_logger, test_table_name, mock_dynamodb, backend_app_dynamodb_table):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture()
def get_account_entity_mock():
    def __inner(project_id: str = "proj-123", id: str = str(uuid.uuid4())):
        current_time = datetime.datetime.fromisoformat("2022-12-01T00:12:00+00:00").isoformat()
        return project_account.ProjectAccount(
            id=id,
            awsAccountId=str(uuid.uuid4()),
            accountType=AccountTypeEnum.USER,
            accountName="fake",
            accountDescription="fake desc",
            createDate=current_time,
            lastUpdateDate=current_time,
            accountStatus=project_account.ProjectAccountStatusEnum.Creating,
            technologyId="tech-123",
            stage=project_account.ProjectAccountStageEnum.DEV,
            region="us-east-1",
            projectId=project_id,
        )

    return __inner


@pytest.fixture()
def get_project_entity_mock():
    def __inner(project_id: str = "proj-123"):
        current_time = datetime.datetime.fromisoformat("2022-12-01T00:12:00+00:00").isoformat()
        return project.Project(
            projectId=project_id,
            projectName="test-name",
            projectDescription="test-description",
            isActive=True,
            createDate=current_time,
            lastUpdateDate=current_time,
        )

    return __inner


@pytest.fixture()
def get_assignment_entity_mock():
    def __inner(user_id: str = "u-0000", project_id="proj-0000"):
        return project_assignment.Assignment(
            userId=user_id,
            projectId=project_id,
            roles=[project_assignment.Role.PLATFORM_USER],
            userEmail="bough@example.com",
            activeDirectoryGroups=[user.ActiveDirectoryGroup(domain="test-domain", groupName="test-group")],
            activeDirectoryGroupStatus=user.UserADStatus.SUCCESS,
        )

    return __inner


@pytest.fixture()
def get_technology_entity_mock():
    def __inner(id: str = "tech-0000", project_id="proj-0000"):
        return technology.Technology(
            id=id,
            project_id=project_id,
            name="test",
            description="desc",
            createDate="2025-02-14",
            lastUpdateDate="2025-02-14",
        )

    return __inner


@pytest.fixture()
def get_enrolment_entity_mock():
    def __inner(
        id: str = "e-0000",
        project_id="proj-0000",
        status=enrolment.EnrolmentStatus.Pending,
    ):
        return enrolment.Enrolment(
            id=id,
            projectId=project_id,
            userId="u-123",
            status=status,
        )

    return __inner


@pytest.fixture()
def get_user_entity_mock():
    def __inner(user_id: str = "user-123"):
        return user.User(
            userId=user_id,
            activeDirectoryGroups=[user.ActiveDirectoryGroup(domain="test", groupName="group")],
            activeDirectoryGroupStatus=user.UserADStatus.SUCCESS,
            userEmail="bough@example.com",
        )

    return __inner
