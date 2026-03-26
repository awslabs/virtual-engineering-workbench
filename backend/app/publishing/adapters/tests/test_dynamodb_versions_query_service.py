import logging
import os
import random
import string
import unittest

import assertpy
import boto3
import moto
import pytest

from app.publishing.adapters.query_services import dynamodb_versions_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.domain.model import version
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

TEST_TABLE_NAME = "test-table"
TEST_REGION = "us-east-1"
TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"
TEST_VERSION_NAME = "1.0.0"
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
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name=TEST_REGION)


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
def sample_versions():
    return [
        version.Version(
            projectId="proj-12345",
            productId="prod-11111111",
            versionId=f"version-{i}",
            scPortfolioId="port-12345",
            versionDescription="Workbench version description",
            versionName=f"{i}.2.3-rc.1",
            versionType=version.VersionType.ReleaseCandidate.text,
            technologyId="tech-12345",
            awsAccountId=f"{i}",
            stage="DEV",
            region="us-east-1",
            originalAmiId=f"ami-{i}",
            status=version.VersionStatus.Creating,
            isRecommendedVersion=True,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
            createdBy="T0037SG",
            lastUpdatedBy="T0037SG",
        )
        for i in range(5)
    ]


@pytest.fixture
def get_test_version():
    def _get_test_version(
        product_id: str = TEST_PRODUCT_ID,
        version_id: str = TEST_VERSION_ID,
        aws_account_id: str = "001234567890",
        status: version.VersionStatus = version.VersionStatus.Created,
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
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId=aws_account_id,
            stage=stage,
            region=region,
            originalAmiId="ami-123",
            status=status,
            scPortfolioId="port-123",
            isRecommendedVersion=is_recommended_version,
            createDate="2000-01-01",
            lastUpdateDate=last_updated_date,
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _get_test_version


def fill_db_with_versions(mock_ddb_repo, versions: list[version.Version]):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(version.VersionPrimaryKey, version.Version)
        for v in versions:
            repo.add(v)
        mock_ddb_repo.commit()


@pytest.mark.parametrize(
    "version_names,expected_version_name,major_version",
    [
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.0.0-rc.2",
                "1.0.0-rc.3",
            ],
            "1.0.0-rc.3",
            None,
        ),
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.0.5-rc.1",
                "1.0.13-rc.1",
            ],
            "1.0.13-rc.1",
            None,
        ),
        pytest.param(
            [
                "1.3.0-rc.1",
                "1.38.0-rc.1",
                "1.112.0-rc.1",
            ],
            "1.112.0-rc.1",
            None,
        ),
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.1.0-rc.1",
                "2.0.1-rc.1",
            ],
            "2.0.1-rc.1",
            None,
        ),
        pytest.param(
            [
                "1.0.0",
                "1.0.1-rc.7",
                "1.1.0-rc.2",
            ],
            "1.1.0-rc.2",
            None,
        ),
        pytest.param(
            [
                "1.0.0",
                "1.5.8",
                "2.3.7",
            ],
            "1.5.8",
            "1",
        ),
        pytest.param(
            [
                "1.2.0",
                "2.2.0",
                "3.2.0",
            ],
            "2.2.0",
            "2",
        ),
    ],
)
def test_get_latest_version_name_return_latest_version_name(
    version_names, expected_version_name, major_version, mock_dynamodb, get_test_version, mock_ddb_repo
):
    # ARRANGE
    query_service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    versions = [
        get_test_version(
            version_name=vers,
            aws_account_id="".join((random.choice(string.digits) for x in range(12))),
        )
        for vers in version_names
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    # ACT
    latest_version_name, latest_version_id = query_service.get_latest_version_name_and_id(
        product_id=TEST_PRODUCT_ID, version_name_begins_with=major_version
    )

    # ASSERT
    assertpy.assert_that(latest_version_name).is_not_none()
    assertpy.assert_that(latest_version_name).is_equal_to(expected_version_name)
    if major_version:
        assertpy.assert_that(latest_version_name.split(".")[0]).is_equal_to(major_version)
    assertpy.assert_that(latest_version_id).is_not_none()


def test_get_latest_version_name_returns_none_when_no_version_found(mock_dynamodb):
    # ARRANGE
    query_service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    latest_version_name, latest_version_id = query_service.get_latest_version_name_and_id(product_id=TEST_PRODUCT_ID)

    # ASSERT
    assertpy.assert_that(latest_version_name).is_none()
    assertpy.assert_that(latest_version_id).is_none()


def test_get_latest_version_name_return_latest_version_name_with_paging(mock_dynamodb, sample_versions, mock_ddb_repo):
    # ARRANGE
    query_service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
        default_page_size=1,
    )
    fill_db_with_versions(mock_ddb_repo, sample_versions)
    # ACT
    latest_version_name, latest_version_id = query_service.get_latest_version_name_and_id(product_id="prod-11111111")
    # ASSERT
    assertpy.assert_that(latest_version_name).is_not_none()
    assertpy.assert_that(latest_version_name).is_equal_to("4.2.3-rc.1")
    assertpy.assert_that(latest_version_id).is_equal_to("version-4")


def test_get_product_version_distributions_should_return_all_distributions_for_version(
    get_test_version, mock_ddb_repo, mock_dynamodb
):
    # ARRANGE
    expected_versions = [
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    versions = [get_test_version(version_id="v-123"), *expected_versions]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID, version_id="v-321")

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_should_return_all_distributions_for_product(
    get_test_version, mock_ddb_repo, mock_dynamodb
):
    # ARRANGE
    versions = [
        get_test_version(version_id="v-123"),
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID)

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(3)
    assertpy.assert_that(versions_from_db).contains_only(*versions)


def test_get_product_version_distributions_should_return_all_distributions_with_paging(
    get_test_version, mock_ddb_repo, mock_dynamodb
):
    # ARRANGE
    expected_versions = [
        get_test_version(version_id="v-321"),
        get_test_version(version_id="v-321", aws_account_id="012345678900"),
    ]
    versions = [get_test_version(version_id="v-123"), *expected_versions]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
        default_page_size=1,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(product_id=TEST_PRODUCT_ID, version_id="v-321")

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_aws_account_ids(get_test_version, mock_ddb_repo, mock_dynamodb):
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
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, version_id=TEST_VERSION_ID, aws_account_ids=["123456789012", "123456789013"]
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(2)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_aws_account_ids_and_recommended_flag(
    get_test_version, mock_ddb_repo, mock_dynamodb
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
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, aws_account_ids=["123456789012", "123456789013"], is_recommended=True
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(4)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distributions_filters_by_region_and_stage(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012", region="eu-west-1", stage="QA"),
        get_test_version(aws_account_id="123456789014", region="eu-west-1", stage="QA"),
        get_test_version(aws_account_id="123456789013", region="eu-west-1", stage="QA"),
        get_test_version(aws_account_id="123456789015", is_recommended_version=False, region="eu-west-1", stage="QA"),
    ]
    versions = [
        get_test_version(
            version_id="vers-1234",
            region="eu-west-1",
        ),
        get_test_version(
            version_id="vers-1235",
        ),
        get_test_version(version_id="vers-1236", region="eu-west-1", stage="PROD"),
        *expected_versions,
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID, stage="QA", region="eu-west-1"
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(4)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_distinct_number_of_versions_count_distinct_ids(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    expected_versions = [
        get_test_version(),
        get_test_version(version_id="vers-321"),
        get_test_version(version_id="vers-111"),
    ]
    versions = [
        get_test_version(product_id="test-prod-1", version_id="vers-111"),
        *expected_versions,
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    # ACT
    distinct_version_ids_count = service.get_distinct_number_of_versions(product_id=TEST_PRODUCT_ID)
    # ASSERT
    assertpy.assert_that(distinct_version_ids_count).is_equal_to(3)


def test_get_distinct_number_of_active_versions(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    versions = [
        get_test_version(),
        get_test_version(version_id="vers-321", status=version.VersionStatus.Retired),
        get_test_version(version_id="vers-111"),
        get_test_version(version_id="vers-111", aws_account_id="123456789"),
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    # ACT
    distinct_version_ids_count = service.get_distinct_number_of_versions(
        product_id=TEST_PRODUCT_ID, status=version.VersionStatus.Created
    )
    # ASSERT
    assertpy.assert_that(distinct_version_ids_count).is_equal_to(2)


def test_get_distinct_number_of_active_rc_versions(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    versions = [
        get_test_version(),
        get_test_version(version_id="vers-321", status=version.VersionStatus.Retired),
        get_test_version(version_id="vers-111"),
        get_test_version(version_id="vers-421"),
        get_test_version(version_id="vers-1111", version_name="1.0.0-rc.1"),
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )
    # ACT
    distinct_version_ids_count = service.get_distinct_number_of_versions(
        product_id=TEST_PRODUCT_ID, status=version.VersionStatus.Created, version_name_filter="-rc."
    )
    # ASSERT
    assertpy.assert_that(distinct_version_ids_count).is_equal_to(1)


def test_get_product_version_distributions_filters_by_statuses(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012", status=version.VersionStatus.Created),
        get_test_version(aws_account_id="123456789013", status=version.VersionStatus.Creating),
        get_test_version(aws_account_id="123456789014", status=version.VersionStatus.Updating),
    ]
    versions = [
        get_test_version(aws_account_id="123456789015", status=version.VersionStatus.Failed),
        get_test_version(aws_account_id="123456789016", status=version.VersionStatus.Retired),
        *expected_versions,
    ]
    fill_db_with_versions(mock_ddb_repo, versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_product_version_distributions(
        product_id=TEST_PRODUCT_ID,
        statuses=[version.VersionStatus.Created, version.VersionStatus.Creating, version.VersionStatus.Updating],
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(3)
    assertpy.assert_that(versions_from_db).contains_only(*expected_versions)


def test_get_product_version_distribution_returns_version_distribution(get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    expected_versions = [
        get_test_version(aws_account_id="123456789012", status=version.VersionStatus.Created),
        get_test_version(aws_account_id="123456789013", status=version.VersionStatus.Creating),
        get_test_version(aws_account_id="123456789014", status=version.VersionStatus.Updating),
    ]

    fill_db_with_versions(mock_ddb_repo, expected_versions)

    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    version_from_db = service.get_product_version_distribution(
        product_id=TEST_PRODUCT_ID, version_id=TEST_VERSION_ID, aws_account_id="123456789012"
    )

    # ASSERT
    assertpy.assert_that(version_from_db).is_equal_to(
        get_test_version(aws_account_id="123456789012", status=version.VersionStatus.Created)
    )


def test_get_all_versions_returns_correct_versions(sample_versions, get_test_version, mock_ddb_repo, mock_dynamodb):
    # ARRANGE
    unrelated_version: version.Version = get_test_version(region="eu-central-1")
    sample_versions.append(unrelated_version)
    fill_db_with_versions(mock_ddb_repo, sample_versions)
    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    versions_from_db = service.get_all_versions(
        region=TEST_REGION,
    )

    # ASSERT
    assertpy.assert_that(versions_from_db).is_length(5)
    assertpy.assert_that(versions_from_db[0].region).is_equal_to(TEST_REGION)


def test_get_used_ami_ids_in_all_versions_returns_ami_id_set(
    sample_versions, get_test_version, mock_ddb_repo, mock_dynamodb
):
    # ARRANGE
    unrelated_version: version.Version = get_test_version(region="eu-central-1")
    sample_versions.append(unrelated_version)
    fill_db_with_versions(mock_ddb_repo, sample_versions)
    service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GSI_NAME_ENTITIES,
    )

    # ACT
    ami_ids = service.get_used_ami_ids_in_all_versions(
        region=TEST_REGION,
    )

    # ASSERT
    assertpy.assert_that(ami_ids).is_length(5)
