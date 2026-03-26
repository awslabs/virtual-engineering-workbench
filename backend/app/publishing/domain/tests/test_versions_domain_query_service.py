import tempfile
from unittest import mock

import assertpy
import pytest

from app.publishing.domain.model import version, version_summary
from app.publishing.domain.ports import template_service, versions_query_service
from app.publishing.domain.query_services import versions_domain_query_service
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    region_value_object,
    stage_value_object,
    version_id_value_object,
)

TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"
TEST_VERSION_NAME = "1.0.0"
TEST_ORIGINAL_AMI_REGION = "us-east-1"


@pytest.fixture
def get_test_version():
    def _get_test_version(
        version_id: str = TEST_VERSION_ID,
        status: version.VersionStatus = version.VersionStatus.Created,
        stage: version.VersionStage = version.VersionStage.DEV,
        version_name: str = TEST_VERSION_NAME,
        last_updated_date: str = "2000-01-01T00:00:00+00:00",
        version_type: str = version.VersionType.Released.text,
        original_ami_id: str = "ami-123",
    ):
        return version.Version(
            projectId="proj-123",
            productId=TEST_PRODUCT_ID,
            technologyId="t-123",
            versionId=version_id,
            versionName=version_name,
            versionDescription="Test Description",
            draftTemplateLocation="prod-12345abc/vers-12345abc/workbench-template.yml",
            versionType=version_type,
            awsAccountId="001234567890",
            stage=stage,
            region="us-east-1",
            originalAmiId=original_ami_id,
            status=status,
            scPortfolioId="port-123",
            isRecommendedVersion=True,
            createDate="2000-01-01T00:00:00+00:00",
            lastUpdateDate=last_updated_date,
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _get_test_version


@pytest.fixture
def file_service_mock():
    file_mock = mock.create_autospec(spec=template_service.TemplateService)
    file_mock.put_template.return_value = None
    file_mock.does_template_exist.return_value = False
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"my product template")
    file_mock.get_template.return_value = temp_file.name
    temp_file.close()
    return file_mock


def test_get_product_version_when_exists_should_aggregate_distributions_into_a_summary(
    get_test_version, file_service_mock
):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2010-01-01T00:00:00+00:00"),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2010-01-01T00:00:00+00:00"),
        get_test_version(stage=version.VersionStage.PROD, last_updated_date="2020-01-01T00:00:00+00:00"),
        get_test_version(stage=version.VersionStage.PROD, last_updated_date="2020-01-01T00:00:00+00:00"),
    ]
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    summary, distributions, draft_template = domain_service.get_product_version(
        product_id=product_id_value_object.from_str("prod-123"), version_id=version_id_value_object.from_str("v-123")
    )

    # ASSERT
    assertpy.assert_that(summary).is_not_none()
    assertpy.assert_that(summary).is_equal_to(
        version_summary.VersionSummary.construct(
            versionId=TEST_VERSION_ID,
            name=TEST_VERSION_NAME,
            description="Test Description",
            versionType=version.VersionType.Released.text,
            stages=[version.VersionStage.DEV, version.VersionStage.QA, version.VersionStage.PROD],
            status=version_summary.VersionSummaryStatus.Created,
            recommendedVersion=True,
            lastUpdate="2020-01-01T00:00:00+00:00",
            lastUpdatedBy="T0011AA",
            originalAmiId="ami-123",
        )
    )

    assertpy.assert_that(distributions).is_length(6)
    assertpy.assert_that(draft_template).is_equal_to("my product template")


def test_get_product_version_when_not_distributed_should_not_contain_a_stage(get_test_version, file_service_mock):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distributions.return_value = [
        get_test_version(version_name="1.0.0-rc.1", version_type=version.VersionType.ReleaseCandidate.text),
        get_test_version(version_name="1.0.0-rc.1", version_type=version.VersionType.ReleaseCandidate.text),
        get_test_version(
            version_name="1.0.0-rc.1",
            version_type=version.VersionType.ReleaseCandidate.text,
            stage=version.VersionStage.QA,
            last_updated_date="2010-01-01T00:00:00+00:00",
        ),
        get_test_version(
            version_name="1.0.0-rc.1",
            version_type=version.VersionType.ReleaseCandidate.text,
            stage=version.VersionStage.QA,
            last_updated_date="2010-01-01T00:00:00+00:00",
        ),
    ]
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    summary, distributions, draft_template = domain_service.get_product_version(
        product_id=product_id_value_object.from_str("prod-123"), version_id=version_id_value_object.from_str("v-123")
    )

    # ASSERT
    assertpy.assert_that(summary).is_not_none()
    assertpy.assert_that(summary).is_equal_to(
        version_summary.VersionSummary.construct(
            versionId=TEST_VERSION_ID,
            name="1.0.0-rc.1",
            description="Test Description",
            versionType=version.VersionType.ReleaseCandidate.text,
            stages=[version.VersionStage.DEV, version.VersionStage.QA],
            status=version_summary.VersionSummaryStatus.Created,
            recommendedVersion=True,
            lastUpdate="2010-01-01T00:00:00+00:00",
            lastUpdatedBy="T0011AA",
            originalAmiId="ami-123",
        )
    )

    assertpy.assert_that(distributions).is_length(4)
    assertpy.assert_that(draft_template).is_equal_to("my product template")


@pytest.mark.parametrize(
    "version_statuses,expected_summary_status",
    [
        pytest.param(
            [
                version.VersionStatus.Created,
                version.VersionStatus.Created,
                version.VersionStatus.Created,
            ],
            version_summary.VersionSummaryStatus.Created,
        ),
        pytest.param(
            [
                version.VersionStatus.Failed,
                version.VersionStatus.Created,
                version.VersionStatus.Created,
            ],
            version_summary.VersionSummaryStatus.Failed,
        ),
        pytest.param(
            [
                version.VersionStatus.Retired,
                version.VersionStatus.Retired,
                version.VersionStatus.Retired,
            ],
            version_summary.VersionSummaryStatus.Retired,
        ),
        pytest.param(
            [
                version.VersionStatus.Creating,
                version.VersionStatus.Created,
                version.VersionStatus.Created,
            ],
            version_summary.VersionSummaryStatus.Processing,
        ),
    ],
)
def test_get_product_version_should_calculate_summary_status_correctly(
    version_statuses, expected_summary_status, get_test_version, file_service_mock
):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distributions.return_value = [
        get_test_version(status=version_statuses[0]),
        get_test_version(status=version_statuses[1]),
        get_test_version(status=version_statuses[2]),
    ]
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    summary, distributions, draft_template = domain_service.get_product_version(
        product_id=product_id_value_object.from_str("prod-123"), version_id=version_id_value_object.from_str("v-123")
    )

    # ASSERT
    assertpy.assert_that(summary).is_not_none()
    assertpy.assert_that(summary.status).is_equal_to(expected_summary_status)


def test_get_versions_ready_for_provisioning_should_return_all_ready_for_provisioning_versions(
    get_test_version, file_service_mock
):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distributions.return_value = [
        get_test_version(stage=version.VersionStage.QA),
        get_test_version(stage=version.VersionStage.QA),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2010-01-01"),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2010-01-01"),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2020-01-01"),
        get_test_version(stage=version.VersionStage.QA, last_updated_date="2020-01-01"),
    ]
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    distributions = domain_service.get_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str("prod-123"),
        stage=stage_value_object.from_str(version.VersionStage.QA),
        region=region_value_object.from_str("us-east-1"),
    )

    # ASSERT
    assertpy.assert_that(distributions).is_not_none()
    assertpy.assert_that(distributions).is_length(6)


def test_get_version_distribution_should_return_version(get_test_version, file_service_mock):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distribution.return_value = get_test_version(stage=version.VersionStage.QA)
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    expected_enriched_version = get_test_version(stage=version.VersionStage.QA).dict()
    expected_enriched_version["amiId"] = get_test_version(stage=version.VersionStage.QA).copiedAmiId

    # ACT
    distribution = domain_service.get_version_distribution(
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=version_id_value_object.from_str(TEST_VERSION_ID),
        aws_account_id=aws_account_id_value_object.from_str("001234567890"),
    )

    # ASSERT
    assertpy.assert_that(distribution).is_not_none()
    assertpy.assert_that(distribution).is_equal_to(expected_enriched_version)


def test_get_latest_major_version_summaries_should_aggregate_major_version_summaries(
    get_test_version, file_service_mock
):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    mock_qs.get_product_version_distributions.return_value = [
        get_test_version(version_id="vers-12345", version_name="1.2.0"),
        get_test_version(version_id="vers-12345", version_name="1.2.0", stage=version.VersionStage.QA),
        get_test_version(version_id="vers-12345", version_name="1.2.0", stage=version.VersionStage.PROD),
        get_test_version(version_id="vers-12346", version_name="1.3.0"),
        get_test_version(version_id="vers-12346", version_name="1.3.0", stage=version.VersionStage.QA),
        get_test_version(version_id="vers-12346", version_name="1.3.0", stage=version.VersionStage.PROD),
        get_test_version(version_id="vers-12347", version_name="2.3.1"),
        get_test_version(version_id="vers-12347", version_name="2.3.1", stage=version.VersionStage.QA),
        get_test_version(version_id="vers-12347", version_name="2.3.1", stage=version.VersionStage.PROD),
        get_test_version(version_id="vers-12348", version_name="2.3.2"),
        get_test_version(version_id="vers-12348", version_name="2.3.2", stage=version.VersionStage.QA),
        get_test_version(version_id="vers-12348", version_name="2.3.2", stage=version.VersionStage.PROD),
        get_test_version(version_id="vers-12349", version_name="3.0.1-rc5"),
        get_test_version(version_id="vers-12349", version_name="3.0.1-rc5", stage=version.VersionStage.QA),
        get_test_version(version_id="vers-12340", version_name="3.1.0-rc2"),
        get_test_version(version_id="vers-12340", version_name="3.1.0-rc2", stage=version.VersionStage.QA),
    ]
    domain_service = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=mock_qs, file_srv=file_service_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    version_summaries = domain_service.get_latest_major_version_summaries(
        product_id=product_id_value_object.from_str("prod-123")
    )

    # ASSERT
    assertpy.assert_that(version_summaries).is_not_none()
    assertpy.assert_that(version_summaries).is_length(3)
    assertpy.assert_that([vers.name for vers in version_summaries]).is_equal_to(["1.3.0", "2.3.2", "3.1.0-rc2"])
