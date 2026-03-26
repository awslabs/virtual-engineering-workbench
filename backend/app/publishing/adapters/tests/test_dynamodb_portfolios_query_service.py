import os

import assertpy
import boto3
import moto
import pytest
from freezegun import freeze_time

from app.publishing.adapters.query_services import dynamodb_portfolios_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.domain.model import portfolio
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
@freeze_time("2023-06-20")
def sample_portfolios():
    return [
        portfolio.Portfolio(
            portfolioId=f"port-{i}abc",
            scPortfolioId=f"port-{i}",
            projectId="proj-12345",
            technologyId="tech-12345",
            awsAccountId=f"{i}",
            stage="DEV",
            region="us-east-1",
            status=portfolio.PortfolioStatus.Created,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
        )
        for i in range(5)
    ]


def fill_db_with_portfolios(mock_ddb_repo, portfolios):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio)
        for portf in portfolios:
            repo.add(portf)
        mock_ddb_repo.commit()


def test_get_portfolios_by_tech_and_stage_return_portfolios_by_tech_and_stage(
    mock_dynamodb, sample_portfolios, mock_ddb_repo
):
    # ARRANGE
    query_service = dynamodb_portfolios_query_service.DynamoDBPortfoliosQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_portfolios(mock_ddb_repo, sample_portfolios)
    # ACT
    portfolios = query_service.get_portfolios_by_tech_and_stage(technology_id="tech-12345", portfolio_stage="DEV")
    # ASSERT
    assertpy.assert_that(portfolios).is_not_none()
    assertpy.assert_that(len(portfolios)).is_equal_to(5)
