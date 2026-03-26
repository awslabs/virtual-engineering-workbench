import os
from datetime import datetime, timezone

import assertpy
import boto3
import moto
import pytest

from app.publishing.adapters.query_services import dynamodb_amis_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.domain.read_models import ami
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

TEST_TABLE_NAME = "test-table"
GSI_NAME_ENTITIES = "gsi_entities"


@pytest.fixture
def mock_ddb_repo(mock_logger, mock_dynamodb):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=TEST_TABLE_NAME).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture(scope="function")
def required_env_vars():
    """Mocked AWS Credentials for moto."""

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


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
            {"AttributeName": "entity", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI_NAME_ENTITIES,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    table.meta.client.get_waiter("table_exists").wait(TableName=TEST_TABLE_NAME)
    return table


@pytest.fixture()
def sample_amis():
    return [
        ami.Ami(
            projectId="proj-12345",
            amiId=f"ami-{str(i)}",
            amiName="Test name",
            amiDescription="Test description",
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        for i in range(5)
    ]


def fill_db_with_amis(mock_ddb_repo, amis):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(ami.AmiPrimaryKey, ami.Ami)
        for ami_item in amis:
            repo.add(ami_item)
        mock_ddb_repo.commit()


def test_get_amis_by_status_returns_amis(mock_dynamodb, sample_amis, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_amis_query_service.DynamoDBAMIsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_amis(mock_ddb_repo, sample_amis)

    # ACT
    amis = query_service.get_amis("proj-12345")

    # ASSERT
    assertpy.assert_that(amis).is_not_none()
    assertpy.assert_that(len(amis)).is_equal_to(5)


def test_get_ami_returns_correct_ami(mock_dynamodb, sample_amis, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_amis_query_service.DynamoDBAMIsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_amis(mock_ddb_repo, sample_amis)

    # ACT
    ami_item = query_service.get_ami(sample_amis[0].amiId)

    # ASSERT
    assertpy.assert_that(ami_item).is_not_none()
    assertpy.assert_that(ami_item.amiId).is_equal_to(sample_amis[0].amiId)


def test_get_ami_returns_none_when_ami_not_found(mock_dynamodb):
    # ARRANGE
    query_service = dynamodb_amis_query_service.DynamoDBAMIsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    ami_item = query_service.get_ami("ami-x")

    # ASSERT
    assertpy.assert_that(ami_item).is_none()
