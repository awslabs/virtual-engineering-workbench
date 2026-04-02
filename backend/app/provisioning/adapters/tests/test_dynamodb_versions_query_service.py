import os

import assertpy
import pytest

from app.provisioning.adapters.query_services import dynamodb_versions_query_service
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.tests.conftest import TEST_COMPONENT_VERSION_DETAILS, TEST_OS_VERSION
from app.provisioning.domain.read_models import version

TEST_TABLE_NAME = "test-table"
TEST_REGION = "us-east-1"
TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"
TEST_VERSION_NAME = "1.0.0"


@pytest.fixture(scope="function")
def required_env_vars():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION


@pytest.fixture
def get_test_version():
    def _get_test_version(
        product_id: str = TEST_PRODUCT_ID,
        version_id: str = TEST_VERSION_ID,
        aws_account_id: str = "001234567890",
        stage: version.VersionStage = version.VersionStage.DEV,
        region: str = TEST_REGION,
        version_name: str = TEST_VERSION_NAME,
        last_updated_date: str = "2000-01-01",
        is_recommended_version: bool = True,
    ):
        return version.Version(
            projectId="proj-123",
            productId=product_id,
            technologyId="t-123",
            versionId=version_id,
            versionName=version_name,
            versionDescription="Test Description",
            awsAccountId=aws_account_id,
            stage=stage,
            accountId="account-id-12345",
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-vers-123",
            isRecommendedVersion=is_recommended_version,
            lastUpdateDate=last_updated_date,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
        )

    return _get_test_version


def fill_db_with_versions(backend_app_dynamodb_table, versions: list[version.Version]):
    for v in versions:
        backend_app_dynamodb_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.PRODUCT.value}#{v.productId}",
                "SK": f"{dynamo_entity_config.DBPrefix.VERSION.value}#{v.versionId}#{dynamo_entity_config.DBPrefix.AWS_ACCOUNT.value}#{v.awsAccountId}",
                **v.model_dump(),
            }
        )


def test_get_product_version_distributions_should_return_all_distributions_for_version(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    expected_versions = [
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    versions = [get_test_version(version_id="v-123"), *expected_versions]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID, version_id="v-321")

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_should_return_all_distributions_for_product(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    versions = [
        get_test_version(version_id="v-123"),
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID)

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(3)
    assertpy.assert_that(versions_from_db).contains_only(*versions)


def test_get_product_version_distributions_should_return_all_distributions_with_paging(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    expected_versions = [
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    versions = [get_test_version(version_id="v-123"), *expected_versions]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        default_page_size=1,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID, version_id="v-321")

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_aws_account_ids(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012"),
        get_test_version(aws_account_id="123456789013"),
    ]
    versions = [
        get_test_version(aws_account_id="123456789014"),
        get_test_version(aws_account_id="123456789015"),
        *expected_versions,
    ]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, version_id=TEST_VERSION_ID, aws_account_ids=["123456789012", "123456789013"]
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_aws_account_ids_and_recommended_flag(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012"),
        get_test_version(aws_account_id="123456789013"),
        get_test_version(aws_account_id="123456789012", version_id="vers-321"),
        get_test_version(aws_account_id="123456789013", version_id="vers-321"),
    ]
    versions = [
        get_test_version(aws_account_id="123456789014"),
        get_test_version(aws_account_id="123456789015"),
        get_test_version(aws_account_id="123456789012", version_id="vers-111", is_recommended_version=False),
        get_test_version(aws_account_id="123456789013", version_id="vers-111", is_recommended_version=False),
        *expected_versions,
    ]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, aws_account_ids=["123456789012", "123456789013"], is_recommended=True
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(4)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_region_and_stage(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_gsi_by_sc_id
):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012", region="eu-west-1", stage="QA"),
        get_test_version(aws_account_id="123456789014", region="eu-west-1", stage="QA"),
        get_test_version(aws_account_id="123456789013", region="eu-west-1", stage="QA"),
        get_test_version(is_recommended_version=False, region="eu-west-1", stage="QA"),
    ]
    versions = [
        get_test_version(
            region="eu-west-1",
        ),
        get_test_version(),
        get_test_version(region="eu-west-1", stage="PROD"),
        *expected_versions,
    ]
    fill_db_with_versions(backend_app_dynamodb_table, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, stage="QA", region="eu-west-1"
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(4)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_by_provisioning_artifact_id_should_return_version(
    get_test_version, backend_app_dynamodb_table, mock_dynamodb, mock_ddb_repo, mock_gsi_by_sc_id
):
    # ARRANGE
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(version.VersionPrimaryKey, version.Version).add(
            get_test_version(aws_account_id="123456789012")
        )
        mock_ddb_repo.get_repository(version.VersionPrimaryKey, version.Version).add(
            get_test_version(aws_account_id="123456789013")
        )
        mock_ddb_repo.commit()

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=mock_gsi_by_sc_id,
    )

    # ACT

    v = service.get_by_provisioning_artifact_id(sc_provisioning_artifact_id="sc-vers-123")

    # ASSERT
    assertpy.assert_that(v).is_not_none()
