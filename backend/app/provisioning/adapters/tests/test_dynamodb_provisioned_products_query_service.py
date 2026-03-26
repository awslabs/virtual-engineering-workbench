import assertpy
import pytest

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.query_services import dynamodb_provisioned_products_query_service
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter

TEST_PROJECT_ID = "proj-123"
TEST_PAGE_SIZE = 100


@pytest.fixture()
def get_sample_provisioned_product():
    def _inner(
        project_id: str = "proj-123",
        provisioned_product_id: str = "pp-123",
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        user_id: str = "T0011AA",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        product_id: str = "prod-123",
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
        experimental: bool = False,
        region: str = "us-east-1",
        product_name: str = "Pied Piper",
        version_name: str = "v1.0.0",
        version_id: str = "vers-123",
    ):
        return provisioned_product.ProvisionedProduct(
            projectId=project_id,
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product_type,
            userId=user_id,
            userDomains=["domain"],
            status=status,
            productId=product_id,
            productName=product_name,
            productDescription="Compression",
            technologyId="tech-123",
            versionId=version_id,
            versionName=version_name,
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value")
            ],
            experimental=experimental,
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _inner


def test_provisioned_products_query_service_get_by_id_should_return_if_exists(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(get_sample_provisioned_product())
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    vt = query_service.get_by_id("pp-123")
    vt_non_existing = query_service.get_by_id("pp-321")

    # ASSERT
    assertpy.assert_that(vt).is_not_none()
    assertpy.assert_that(vt_non_existing).is_none()


def test_provisioned_products_query_service_get_by_sc_provisioned_product_id_should_return_if_exists(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(get_sample_provisioned_product(sc_provisioned_product_id="pp-321"))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    vt = query_service.get_by_sc_provisioned_product_id("pp-321")
    vt_non_existing = query_service.get_by_sc_provisioned_product_id("pp-456")

    # ASSERT
    assertpy.assert_that(vt).is_not_none()
    assertpy.assert_that(vt_non_existing).is_none()


def test_get_provisioned_products_by_user_id_should_return_provisioned_products_by_user(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(get_sample_provisioned_product(user_id="SE15686"))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    virtual_target_response = query_service.get_provisioned_products_by_user_id(
        project_id="proj-123",
        user_id="SE15686",
    )

    # ASSERT
    assertpy.assert_that(virtual_target_response).is_length(1)


def test_get_provisioned_products_by_user_id_should_return_provisioned_products_by_type(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(
            get_sample_provisioned_product(user_id="SE15686"),
        )
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(
            get_sample_provisioned_product(
                user_id="SE15686",
                provisioned_product_type=provisioned_product.ProvisionedProductType.Workbench,
                provisioned_product_id="pp-321",
            ),
        )
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    virtual_target_response = query_service.get_provisioned_products_by_user_id(
        project_id="proj-123",
        user_id="SE15686",
        provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
    )

    # ASSERT
    assertpy.assert_that(virtual_target_response).is_length(1)


def test_get_provisioned_products_by_user_id_should_return_virtual_targets_by_stage_and_status(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(
            get_sample_provisioned_product(user_id="SE15686"),
        )
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(
            get_sample_provisioned_product(
                user_id="SE15686", stage=provisioned_product.ProvisionedProductStage.QA, provisioned_product_id="pp-456"
            ),
        )
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(
            get_sample_provisioned_product(
                user_id="SE15686", status=product_status.ProductStatus.Terminated, provisioned_product_id="pp-789"
            )
        )
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(get_sample_provisioned_product(user_id="SE15686", provisioned_product_id="pp-321", product_id="prod-321"))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    virtual_target_response = query_service.get_provisioned_products_by_user_id(
        project_id="proj-123",
        user_id="SE15686",
        stage=provisioned_product.ProvisionedProductStage.DEV,
        exclude_status=[product_status.ProductStatus.Terminated],
        product_id="prod-123",
    )

    # ASSERT
    assertpy.assert_that(virtual_target_response).is_length(1)


def test_get_provisioned_product_should_return_provisioned_product(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(get_sample_provisioned_product(provisioned_product_id="vt-1"))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    virtual_target_response = query_service.get_provisioned_product(
        project_id="proj-123",
        provisioned_product_id="vt-1",
    )

    # ASSERT
    assertpy.assert_that(virtual_target_response).is_not_none()
    assertpy.assert_that(virtual_target_response).is_equal_to(
        provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId="vt-1",
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=None,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value")
            ],
            experimental=False,
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )
    )


def test_get_all_provisioned_products_should_return_all(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(50):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(get_sample_provisioned_product(provisioned_product_id=f"vt-{i}"))

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products()

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}" for i in range(50)]
    )


def test_get_all_cross_projects_provisioned_products_should_return_all(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(50):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(get_sample_provisioned_product(provisioned_product_id=f"vt-{i}"))

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    # initial request
    provisioned_products_response, last_key = query_service.get_all_cross_projects_provisioned_products(page_size=25)
    # Next request
    next_provisioned_products_response, last_key = query_service.get_all_cross_projects_provisioned_products(
        start_key=last_key, page_size=25
    )

    # ASSERT
    assertpy.assert_that(len(provisioned_products_response)).is_equal_to(25)
    assertpy.assert_that(len(next_provisioned_products_response)).is_equal_to(25)
    combined_provisioned_products_response = [*provisioned_products_response, *next_provisioned_products_response]
    assertpy.assert_that({pp.provisionedProductId for pp in combined_provisioned_products_response}).contains_only(
        *[f"vt-{i}" for i in range(50)]
    )


def test_get_all_provisioned_products_should_return_all_active(
    mock_table_name,
    mock_dynamodb,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(50):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}", status=product_status.ProductStatus.Terminated
                )
            )

            mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )
    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products(exclude_terminated=True)

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).is_empty()


def test_get_provisioned_products_by_project_id_should_return_provisioned_products_by_project_id(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        )
        repo.add(get_sample_provisioned_product())
        repo.add(get_sample_provisioned_product(provisioned_product_id="pp-234"))
        repo.add(get_sample_provisioned_product(project_id="proj-345", provisioned_product_id="pp-345"))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products = query_service.get_provisioned_products_by_project_id(
        project_id="proj-123",
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(2)


def test_get_provisioned_products_by_project_id_should_return_provisioned_products_filtered_by_provisioning_parameters(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        )
        repo.add(get_sample_provisioned_product())
        repo.add(get_sample_provisioned_product(provisioned_product_id="pp-234", experimental=True))
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products = query_service.get_provisioned_products_by_project_id(
        project_id="proj-123",
        experimental=True,
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(1)


def test_get_provisioned_products_by_project_id_should_return_provisioned_products_by_status(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        )
        repo.add(get_sample_provisioned_product())
        repo.add(get_sample_provisioned_product(provisioned_product_id="pp-234"))
        repo.add(
            get_sample_provisioned_product(
                provisioned_product_id="pp-345",
                status=product_status.ProductStatus.Terminated,
            ),
        )
        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products = query_service.get_provisioned_products_by_project_id(
        project_id="proj-123", exclude_status=[product_status.ProductStatus.Terminated]
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(2)


def test_get_provisioned_products_by_product_id_should_only_return_active_provisioned_products(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    product_id="prod-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    product_id="prod-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    product_id="prod-321",
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products_by_product_id(product_id="prod-123")

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-prov" for i in range(10)]
    )


def test_get_provisioned_products_by_product_id_should_only_return_filtered_by_stage_provisioned_products(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    product_id="prod-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    product_id="prod-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    product_id="prod-123",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products_by_product_id(
        product_id="prod-123", stage="QA"
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-running" for i in range(10)]
    )


def test_get_provisioned_products_by_product_id_should_only_return_filtered_by_stage_and_region_provisioned_products(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    product_id="prod-123",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    product_id="prod-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    product_id="prod-123",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="eu-west-3",
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products_by_product_id(
        product_id="prod-123", stage="QA", region="eu-west-3"
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-running" for i in range(10)]
    )


def test_get_provisioned_products_by_product_id_should_filter_by_stage_region_and_version(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    product_id="prod-123",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    product_id="prod-123",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="eu-west-3",
                    version_id="vers-1",
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products_by_product_id(
        product_id="prod-123", stage="QA", region="eu-west-3", version_id="vers-1"
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-running" for i in range(10)]
    )


def test_get_provisioned_products_by_product_id_should_raise_if_region_provided_but_no_stage(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as e:
        next(query_service.get_all_provisioned_products_by_product_id(product_id="prod-123", region="eu-west-3"), None)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("stage parameter must also be provided when region is provided")


def test_update_provisioned_product_status_should_succeed(
    mock_ddb_repo, get_sample_provisioned_product, backend_app_dynamodb_table
):
    # ARRANGE
    pp = get_sample_provisioned_product(
        provisioned_product_id="pp-123",
        status=product_status.ProductStatus.Running,
    )

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).add(pp)

        mock_ddb_repo.commit()

    # ACT
    pp.status = product_status.ProductStatus.Terminated

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        ).update_entity(
            provisioned_product.ProvisionedProductPrimaryKey(
                projectId="proj-123",
                provisionedProductId="pp-123",
            ),
            pp,
        )

        mock_ddb_repo.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "PROJECT#proj-123", "SK": "PROVISIONED_PRODUCT#pp-123"})
    assertpy.assert_that(item.get("Item")).contains_entry(
        {"QSK_3": "PROVISIONED_PRODUCT#INACTIVE#DEV#us-east-1#pp-123"}
    )


def test_get_active_provisioned_products_by_project_id_should_only_return_active_provisioned_products(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    project_id="proj-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    project_id="proj-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    project_id="proj-321",
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_active_provisioned_products_by_project_id(project_id="proj-123")

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-prov" for i in range(10)]
    )


def test_get_active_provisioned_products_by_project_id_should_filter_by_product_type(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    project_id="proj-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    project_id="proj-123",
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    project_id="proj-123",
                    provisioned_product_type=provisioned_product.ProvisionedProductType.Workbench,
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_active_provisioned_products_by_project_id(
        project_id="proj-123", provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}-prov" for i in range(10)]
    )


@pytest.mark.parametrize(
    "product_name,owner,version_name,status,stage,experimental,provisioned_product_type,query_number",
    [
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Running,
            provisioned_product.ProvisionedProductStage.DEV,
            False,
            provisioned_product.ProvisionedProductType.VirtualTarget,
            100,
        ),
        # (
        #     "Pied Piper",
        #     "T0011AA",
        #     "v1.0.0",
        #     product_status.ProductStatus.Terminated,
        #     provisioned_product.ProvisionedProductStage.QA,
        #     True,
        #     provisioned_product.ProvisionedProductType.Workbench,
        #     0
        # ),
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Provisioning,
            provisioned_product.ProvisionedProductStage.PROD,
            False,
            provisioned_product.ProvisionedProductType.VirtualTarget,
            100,
        ),
    ],
)
def test_get_provisioned_products_by_project_id_paginated_paginates_query_result_if_page_overflow(
    product_name,
    owner,
    version_name,
    status,
    stage,
    experimental,
    provisioned_product_type,
    query_number,
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        # Add 303 items provisioned products
        for i in range(101):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.PROD,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.Workbench,
                    experimental=True,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.DEV,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

        mock_ddb_repo.commit()
    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products, paging_token = query_service.get_provisioned_products_by_project_id_paginated(
        project_id="proj-123",
        page_size=TEST_PAGE_SIZE,
        paging_key=None,
        product_name=product_name,
        status=status,
        stage=stage,
        experimental=experimental,
        provisioned_product_type=provisioned_product_type,
    )

    next_provisioned_products, new_paging_token = query_service.get_provisioned_products_by_project_id_paginated(
        project_id="proj-123",
        page_size=TEST_PAGE_SIZE,
        paging_key=paging_token,
        product_name=product_name,
        status=status,
        stage=stage,
        experimental=experimental,
        provisioned_product_type=provisioned_product_type,
    )

    # ASSERT
    assertpy.assert_that(len(provisioned_products)).is_equal_to(query_number)
    assertpy.assert_that(paging_token).is_not_none()

    assertpy.assert_that(len(next_provisioned_products)).is_equal_to(1)
    assertpy.assert_that(new_paging_token).is_none()


@pytest.mark.parametrize(
    "product_name,owner,version_name,status,stage,experimental,provisioned_product_type,query_number",
    [
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Terminated,
            provisioned_product.ProvisionedProductStage.QA,
            True,
            provisioned_product.ProvisionedProductType.Workbench,
            0,
        )
    ],
)
def test_get_provisioned_products_by_project_id_paginated_query_result_if_many_pages_and_filter_terminated(
    product_name,
    owner,
    version_name,
    status,
    stage,
    experimental,
    provisioned_product_type,
    query_number,
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        # Add 303 items provisioned products
        for i in range(101):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.PROD,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.Workbench,
                    experimental=True,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.DEV,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

        mock_ddb_repo.commit()
    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products, paging_token = query_service.get_provisioned_products_by_project_id_paginated(
        project_id="proj-123",
        page_size=TEST_PAGE_SIZE,
        paging_key=None,
        product_name=product_name,
        status=status,
        stage=stage,
        experimental=experimental,
        provisioned_product_type=provisioned_product_type,
    )

    # ASSERT
    assertpy.assert_that(len(provisioned_products)).is_equal_to(query_number)
    assertpy.assert_that(paging_token).is_none()


@pytest.mark.parametrize(
    "product_name,owner,version_name,status,stage,experimental,provisioned_product_type,query_number",
    [
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Running,
            provisioned_product.ProvisionedProductStage.DEV,
            False,
            provisioned_product.ProvisionedProductType.VirtualTarget,
            50,
        ),
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Terminated,
            provisioned_product.ProvisionedProductStage.QA,
            True,
            provisioned_product.ProvisionedProductType.Workbench,
            0,
        ),
        (
            "Pied Piper",
            "T0011AA",
            "v1.0.0",
            product_status.ProductStatus.Provisioning,
            provisioned_product.ProvisionedProductStage.PROD,
            False,
            provisioned_product.ProvisionedProductType.VirtualTarget,
            50,
        ),
    ],
)
def test_get_provisioned_products_by_project_id_paginated_paginates_query_result_on_single_page(
    product_name,
    owner,
    version_name,
    status,
    stage,
    experimental,
    provisioned_product_type,
    query_number,
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        # Add 150 items provisioned products
        for i in range(50):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-prov",
                    status=product_status.ProductStatus.Provisioning,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.PROD,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-term",
                    status=product_status.ProductStatus.Terminated,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.Workbench,
                    experimental=True,
                )
            )

            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}-running",
                    status=product_status.ProductStatus.Running,
                    project_id=TEST_PROJECT_ID,
                    stage=provisioned_product.ProvisionedProductStage.DEV,
                    provisioned_product_type=provisioned_product.ProvisionedProductType.VirtualTarget,
                    experimental=False,
                )
            )

        mock_ddb_repo.commit()
    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products, paging_token = query_service.get_provisioned_products_by_project_id_paginated(
        project_id="proj-123",
        page_size=TEST_PAGE_SIZE,
        paging_key=None,
        product_name=product_name,
        status=status,
        stage=stage,
        experimental=experimental,
        provisioned_product_type=provisioned_product_type,
    )

    # ASSERT
    assertpy.assert_that(len(provisioned_products)).is_equal_to(query_number)
    assertpy.assert_that(paging_token).is_none()


def test_get_all_provisioned_products_should_filter_by_status(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(10):
            repo = mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            )
            repo.add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt1-{i}", status=product_status.ProductStatus.Running
                )
            )
            repo.add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt2-{i}", status=product_status.ProductStatus.Stopped
                )
            )
            repo.add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt3-{i}", status=product_status.ProductStatus.Provisioning
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products(
        status=product_status.ProductStatus.Running
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt1-{i}" for i in range(10)]
    )


def get_all_provisioned_products_by_status_should_return_all(
    mock_table_name,
    mock_dynamodb,
    mock_logger,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    with mock_ddb_repo:
        for i in range(50):
            mock_ddb_repo.get_repository(
                provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
            ).add(
                get_sample_provisioned_product(
                    provisioned_product_id=f"vt-{i}",
                    status=product_status.ProductStatus.Running if i % 2 == 0 else product_status.ProductStatus.Stopped,
                )
            )

        mock_ddb_repo.commit()

    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    # ACT
    provisioned_products_response = query_service.get_all_provisioned_products_by_status(
        status=product_status.ProductStatus.Running
    )

    # ASSERT
    assertpy.assert_that({pp.provisionedProductId for pp in provisioned_products_response}).contains_only(
        *[f"vt-{i}" for i in range(0, 50, 2)]
    )
