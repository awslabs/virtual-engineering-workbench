from unittest import mock

import assertpy
import pytest

from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.query_services import versions_domain_query_service
from app.provisioning.domain.read_models import version
from app.provisioning.domain.tests.product_provisioning.conftest import TEST_COMPONENT_VERSION_DETAILS, TEST_OS_VERSION
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    region_value_object,
    version_stage_value_object,
)


@pytest.fixture
def mock_product_version():
    def _inner(
        stage: version.VersionStage = version.VersionStage.DEV,
        region: str = "us-east-1",
        version_id: str = "ver-123",
    ):
        return version.Version(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            versionId=version_id,
            versionName="v1.0.0",
            versionDescription="Initial release",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            isRecommendedVersion=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            parameters=[
                version.VersionParameter(
                    parameterKey="SomeParam",
                    defaultValue="some-default",
                    parameterType="String",
                    parameterMetadata=version.ParameterMetadata(
                        label="Some Parameter",
                        optionLabels={
                            "val-1": "Value 1",
                            "val-2": "Value 2",
                        },
                    ),
                    parameterConstraints=version.ParameterConstraints(allowedValues=["val-1", "val-2"]),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                    isTechnicalParameter=True,
                ),
            ],
            lastUpdateDate="2023-12-05",
        )

    return _inner


@pytest.fixture()
def versions_query_service_mock():
    versions_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    return versions_qry_srv_mock


def test_get_versions_ready_for_provisioning_returns_correct_versions(
    versions_query_service_mock,
    mock_product_version,
):
    # ARRANGE
    sample_versions = [
        mock_product_version(),
        mock_product_version(),
    ]

    versions_query_service_mock.get_product_version_distributions.return_value = sample_versions
    versions_domain_qry_srv = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=versions_query_service_mock,
    )

    # ACT
    versions = versions_domain_qry_srv.get_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str("prod-123"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
    )

    # ASSERT
    assertpy.assert_that(versions).is_length(len(sample_versions))
    versions_query_service_mock.get_product_version_distributions.assert_called_with(
        product_id="prod-123", stage=version.VersionStage.DEV, region="us-east-1"
    )
    assertpy.assert_that(versions[0].parameters).is_length(2)
    assertpy.assert_that(versions[0].parameters[1].isTechnicalParameter).is_true()


def test_get_versions_ready_for_provisioning_filters_technical_parameters(
    versions_query_service_mock,
    mock_product_version,
):
    # ARRANGE
    sample_versions = [
        mock_product_version(),
        mock_product_version(),
    ]

    versions_query_service_mock.get_product_version_distributions.return_value = sample_versions
    versions_domain_qry_srv = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=versions_query_service_mock,
    )

    # ACT
    versions = versions_domain_qry_srv.get_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str("prod-123"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        return_technical_params=False,
    )

    # ASSERT
    assertpy.assert_that(versions).is_length(len(sample_versions))
    versions_query_service_mock.get_product_version_distributions.assert_called_with(
        product_id="prod-123", stage=version.VersionStage.DEV, region="us-east-1"
    )
    assertpy.assert_that(versions[0].parameters).is_length(1)
    assertpy.assert_that(versions[0].parameters[0].isTechnicalParameter).is_false()
