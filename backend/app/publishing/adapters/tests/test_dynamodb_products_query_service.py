import logging
import os
import unittest

import assertpy
import boto3
import moto
import pytest

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.adapters.query_services import dynamodb_products_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.domain.model import product
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
def get_sample_product():
    def _get_sample_product(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
        status=product.ProductStatus.Created,
        product_type=product.ProductType.Workbench,
    ):
        return product.Product(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            technologyName="Test technology",
            status=status,
            productName="Product Name",
            productType=product_type,
            availableStages=available_stages,
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )

    return _get_sample_product


def fill_db_with_products(mock_ddb_repo, products):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(product.ProductPrimaryKey, product.Product)
        for prod in products:
            repo.add(prod)
        mock_ddb_repo.commit()


def test_get_products_by_project_id_returns_correct_products(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),
            get_sample_product(product_id="prod-3"),
            get_sample_product(product_id="prod-4"),
            get_sample_product(product_id="prod-5"),
        ],
    )

    # ACT
    products = query_service.get_products(project_id="proj-12345")

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(5)


def test_can_get_single_product_by_product_id(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),
            get_sample_product(product_id="prod-3"),
            get_sample_product(product_id="prod-4"),
            get_sample_product(product_id="prod-5"),
        ],
    )

    # ACT
    product = query_service.get_product(project_id="proj-12345", product_id="prod-2")

    # ASSERT
    assertpy.assert_that(product).is_not_none()
    assertpy.assert_that(product).is_equal_to(get_sample_product(product_id="prod-2"))


def test_can_raise_adapter_exception_when_product_not_found(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),
            get_sample_product(product_id="prod-3"),
            get_sample_product(product_id="prod-4"),
            get_sample_product(product_id="prod-5"),
        ],
    )

    # ACT
    with pytest.raises(adapter_exception.AdapterException):
        query_service.get_product(project_id="proj-12345", product_id="prod-6")


def test_get_products_filters_by_stages(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(
                product_id="prod-2", available_stages=[product.ProductStage.DEV, product.ProductStage.QA]
            ),
            get_sample_product(
                product_id="prod-3", available_stages=[product.ProductStage.DEV, product.ProductStage.QA]
            ),
            get_sample_product(
                product_id="prod-4",
                available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
            ),
            get_sample_product(
                product_id="prod-5",
                available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
            ),
        ],
    )

    # ACT
    products = query_service.get_products(
        project_id="proj-12345", available_stages=[product.ProductStage.QA, product.ProductStage.PROD]
    )

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(4)


def test_get_products_filters_by_status(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),
            get_sample_product(product_id="prod-3", status=product.ProductStatus.Archived),
            get_sample_product(product_id="prod-4", status=product.ProductStatus.Creating),
            get_sample_product(product_id="prod-5", status=product.ProductStatus.Failed),
        ],
    )

    # ACT
    products = query_service.get_products(project_id="proj-12345", status=product.ProductStatus.Created)

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(2)


def test_get_products_filters_by_stages_and_status(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(
                product_id="prod-2", available_stages=[product.ProductStage.DEV, product.ProductStage.QA]
            ),
            get_sample_product(
                product_id="prod-3",
                available_stages=[product.ProductStage.DEV, product.ProductStage.QA],
                status=product.ProductStatus.Archived,
            ),
            get_sample_product(
                product_id="prod-4",
                available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
                status=product.ProductStatus.Creating,
            ),
            get_sample_product(
                product_id="prod-5",
                available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
                status=product.ProductStatus.Failed,
            ),
        ],
    )

    # ACT
    products = query_service.get_products(
        project_id="proj-12345",
        available_stages=[product.ProductStage.QA, product.ProductStage.PROD],
        status=product.ProductStatus.Created,
    )

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(1)
    assertpy.assert_that(products[0].productId).is_equal_to("prod-2")


def test_get_products_filters_by_product_type(mock_dynamodb, get_sample_product, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    fill_db_with_products(
        mock_ddb_repo,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),  # TODO: Add more test data when we have more product types
        ],
    )

    # ACT
    products = query_service.get_products(project_id="proj-12345", product_type=product.ProductType.Workbench)

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(2)
