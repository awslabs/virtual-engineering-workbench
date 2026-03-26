import logging
import os
import typing
import unittest
from datetime import datetime, timezone

import assertpy
import boto3
import moto
import pytest

from app.publishing.adapters.query_services import dynamodb_shared_amis_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.domain.model import shared_ami
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

TEST_TABLE_NAME = "test-table"
GSI_NAME_ENTITIES = "gsi_entities"


@pytest.fixture
def mock_logger():
    return unittest.mock.create_autospec(spec=logging.Logger)


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


@pytest.fixture()
def sample_shared_amis():
    return [
        shared_ami.SharedAmi(
            originalAmiId="ami-12345",
            copiedAmiId=f"ami-4234{str(i)}",
            awsAccountId=f"12345678901{str(i)}",
            region=f"eu-west-{i}",
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        for i in range(5)
    ]


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


def fill_db_with_shared_amis(mock_ddb_repo, amis: typing.List[shared_ami.SharedAmi]):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(shared_ami.SharedAmiPrimaryKey, shared_ami.SharedAmi)
        for ami_item in amis:
            repo.add(ami_item)
        mock_ddb_repo.commit()


def test_get_shared_amis_returns_existing_shared_amis(mock_dynamodb, sample_shared_amis, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_shared_amis_query_service.DynamoDBSharedAMIsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_shared_amis(mock_ddb_repo, sample_shared_amis)

    # ACT
    shared_amis = query_service.get_shared_amis(original_ami_id="ami-12345")

    # ASSERT
    assertpy.assert_that(shared_amis).is_not_none()
    assertpy.assert_that(shared_amis).is_length(5)
    assertpy.assert_that(shared_amis[0].originalAmiId).is_equal_to("ami-12345")
