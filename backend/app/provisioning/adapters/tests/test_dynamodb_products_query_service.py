import assertpy
import pytest

from app.provisioning.adapters.query_services import dynamodb_products_query_service
from app.provisioning.adapters.repository.dynamo_entity_config import DBPrefix
from app.provisioning.adapters.tests import conftest
from app.provisioning.domain.read_models import product


@pytest.fixture()
def get_sample_product():
    def _get_sample_product(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
        product_type=product.ProductType.Workbench,
    ):
        return product.Product(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            technologyName="Test technology",
            productName="Product Name",
            productType=product_type,
            availableStages=available_stages,
            availableRegions=["us-east-1", "eu-west-3"],
            lastUpdateDate="2023-09-01T00:00:00+00:00",
        )

    return _get_sample_product


def fill_db_with_products(backend_app_dynamodb_table, products: list[product.Product]):
    for prod in products:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{DBPrefix.PROJECT.value}#{prod.projectId}",
                "SK": f"{DBPrefix.PRODUCT.value}#{prod.productId}",
                **prod.dict(),
            }
        )


def test_get_products_by_project_id_returns_correct_products(
    mock_dynamodb, get_sample_product, backend_app_dynamodb_table
):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
    )
    fill_db_with_products(
        backend_app_dynamodb_table,
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


def test_get_products_filters_by_stages(mock_dynamodb, get_sample_product, backend_app_dynamodb_table):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
    )
    fill_db_with_products(
        backend_app_dynamodb_table,
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


def test_get_products_filters_by_product_type(mock_dynamodb, get_sample_product, backend_app_dynamodb_table):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=conftest.TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
    )
    fill_db_with_products(
        backend_app_dynamodb_table,
        [
            get_sample_product(),
            get_sample_product(product_id="prod-2"),
            get_sample_product(product_id="prod-3", product_type=product.ProductType.VirtualTarget),
            get_sample_product(product_id="prod-4", product_type=product.ProductType.VirtualTarget),
        ],
    )

    # ACT
    products = query_service.get_products(project_id="proj-12345", product_type=product.ProductType.Workbench)

    # ASSERT
    assertpy.assert_that(products).is_not_none()
    assertpy.assert_that(len(products)).is_equal_to(2)


def test_get_products_paging(mock_dynamodb, get_sample_product, backend_app_dynamodb_table):
    # ARRANGE
    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=conftest.TEST_TABLE_NAME, dynamodb_client=mock_dynamodb.meta.client, default_page_size=1
    )
    fill_db_with_products(
        backend_app_dynamodb_table,
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


def test_get_product_should_return_when_exists(
    mock_table_name, mock_dynamodb, mock_logger, get_sample_product, mock_ddb_repo
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(product.ProductPrimaryKey, product.Product).add(get_sample_product())
        mock_ddb_repo.commit()

    query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
    )

    # ACT
    product_response = query_service.get_product(project_id="proj-12345", product_id="prod-1")
    product_response_non_existing = query_service.get_product(project_id="proj-12345", product_id="prod-2")

    # ASSERT
    assertpy.assert_that(product_response).is_equal_to(
        product.Product(
            projectId="proj-12345",
            productId="prod-1",
            technologyId="tech-12345",
            technologyName="Test technology",
            productName="Product Name",
            productType=product.ProductType.Workbench,
            availableStages=[product.ProductStage.DEV],
            availableRegions=["us-east-1", "eu-west-3"],
            lastUpdateDate="2023-09-01T00:00:00+00:00",
        )
    )
    assertpy.assert_that(product_response_non_existing).is_none()
