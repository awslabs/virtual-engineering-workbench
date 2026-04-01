from unittest import mock

import pytest

from app.provisioning.domain.ports import products_query_service, versions_query_service
from app.provisioning.domain.read_models import (
    component_version_detail,
    product,
    version,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]
TEST_COMPONENT_VERSION_DETAILS_DUMPED = [cvd.model_dump() for cvd in TEST_COMPONENT_VERSION_DETAILS]


@pytest.fixture
def versions_repo_mock():
    vers_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)
    return vers_repo_mock


@pytest.fixture()
def get_sample_product():
    def _get_sample_product(product_type=product.ProductType.Workbench):
        return product.Product(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            technologyName="BRAIN",
            productName="mock_product_name",
            productType=product_type,
            productDescription="Mock product description",
            availableStages=[],
            availableRegions=[],
            pausedStages=[],
            pausedRegions=[],
            lastUpdateDate="2023-10-25T00:00:00+00:00",
        )

    return _get_sample_product


@pytest.fixture
def products_repo_mock(get_sample_product):
    prod_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)
    prod_repo_mock.get.return_value = get_sample_product
    return prod_repo_mock


@pytest.fixture
def uow_mock(versions_repo_mock, products_repo_mock):
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork, instance=True)
    repos_dict = {
        version.Version: versions_repo_mock,
        product.Product: products_repo_mock,
    }
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    return uow_mock


@pytest.fixture()
def versions_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    return qry_svc


@pytest.fixture()
def product_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    return qry_svc


@pytest.fixture()
def get_sample_version():
    def _get_sample_version(
        index,
        stage=version.VersionStage.DEV,
        time="2023-10-25T00:00:00+00:00",
        is_recommended=True,
    ):
        return version.Version(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            versionId=f"vers-{index}",
            versionName="1.0.0",
            versionDescription="version description",
            awsAccountId="105249321508",
            accountId="acct-12345",
            stage=stage,
            region="us-east-1",
            amiId="ami-12345",
            scProductId="prod-12345",
            scProvisioningArtifactId="pa-12345",
            isRecommendedVersion=is_recommended,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            parameters=[
                version.VersionParameter(
                    parameterKey=f"{i}",
                    defaultValue="mock-value",
                    description="mock-description",
                    isNoEcho=False,
                    parameterType="mock-param-type",
                    parameterMetadata=version.ParameterMetadata(label="mock-label", optionLabels={"test": "label"}),
                    parameterConstraints=version.ParameterConstraints(
                        allowedPattern="mock-pattern",
                        allowedValues=["mock", "values"],
                        constraintDescription="mock-constraint-description",
                        maxLength="100",
                        maxValue="100",
                        minLength="100",
                        minValue="0",
                    ),
                    isTechnicalParameter=(True if i % 2 else False),
                )
                for i in range(5)
            ],
            lastUpdateDate=time,
        )

    return _get_sample_version


@pytest.fixture()
def get_sample_versions(get_sample_version):
    def _get_sample_versions(
        stage: version.VersionStage = version.VersionStage.DEV,
        time="2023-10-25T00:00:00+00:00",
        start_index=0,
        is_recommended=True,
    ):
        return [get_sample_version(i, stage, time, is_recommended) for i in range(start_index, 5)]

    return _get_sample_versions
