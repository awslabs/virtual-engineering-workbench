from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.model import product, version, version_summary
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.publishing.domain.query_services import products_domain_query_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    product_type_value_object,
    project_id_value_object,
    user_role_value_object,
)
from app.shared.middleware.authorization import VirtualWorkbenchRoles

TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"
TEST_VERSION_NAME = "1.0.0"


@pytest.fixture()
def get_sample_product():
    def _get_sample_product(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
    ):
        return product.Product(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName="Product Name",
            productType=product.ProductType.Workbench,
            availableStages=available_stages,
            availableRegions=["us-east-1"],
            createDate="2023-07-07T00:00:00+00:00",
            lastUpdateDate="2023-07-07T00:00:00+00:00",
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )

    return _get_sample_product


def find_product(products: list[product.Product], product_id: str) -> product.Product:
    for p in products:
        if p.productId == product_id:
            return p
    return None


@pytest.fixture
def get_test_version():
    def _get_test_version(
        version_id: str = TEST_VERSION_ID,
        status: version.VersionStatus = version.VersionStatus.Created,
        stage: version.VersionStage = version.VersionStage.DEV,
        version_name: str = TEST_VERSION_NAME,
        last_updated_date: str = "2000-01-01",
        last_updated_by: str = "T0011AA",
    ):
        return version.Version(
            projectId="proj-123",
            productId=TEST_PRODUCT_ID,
            technologyId="t-123",
            versionId=version_id,
            versionName=version_name,
            versionDescription="Test Description",
            versionType=version.VersionType.Released.text,
            awsAccountId="001234567890",
            stage=stage,
            region="us-east-1",
            originalAmiId="ami-123",
            status=status,
            scPortfolioId="port-123",
            isRecommendedVersion=True,
            createDate="2000-01-01",
            lastUpdateDate=last_updated_date,
            createdBy="T0011AA",
            lastUpdatedBy=last_updated_by,
            restoredFromVersionName="1.0.0",
        )

    return _get_test_version


@pytest.fixture()
def products_query_service_mock(get_sample_product):
    products_qry_srv_mock = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    sample_products = [
        get_sample_product(),
        get_sample_product(product_id="prod-2"),
        get_sample_product(product_id="prod-3"),
        get_sample_product(product_id="prod-4"),
        get_sample_product(product_id="prod-5"),
    ]
    products_qry_srv_mock.get_products.return_value = sample_products
    products_qry_srv_mock.get_product.side_effect = lambda project_id, product_id: find_product(
        sample_products, product_id
    )
    return products_qry_srv_mock


@pytest.fixture()
def versions_query_service_mock(get_test_version):
    versions_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    versions_qry_srv_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(),
        get_test_version(
            version_id="v-000", version_name="2.0.0", stage=version.VersionStage.QA, last_updated_date="2010-01-01"
        ),
        get_test_version(
            version_id="v-000", version_name="2.0.0", stage=version.VersionStage.QA, last_updated_date="2010-01-01"
        ),
        get_test_version(
            version_id="v-111",
            version_name="3.0.0",
            stage=version.VersionStage.PROD,
            last_updated_date="2020-01-01",
            last_updated_by="T0012AB",
        ),
        get_test_version(
            version_id="v-111",
            version_name="3.0.0",
            stage=version.VersionStage.PROD,
            last_updated_date="2020-01-01",
            last_updated_by="T0012AB",
        ),
    ]
    return versions_qry_srv_mock


@freeze_time("2023-07-07T00:00:00+00:00")
def test_get_products_returns_correct_products(
    products_query_service_mock, versions_query_service_mock, get_sample_product
):
    # ARRANGE
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
    )

    # ACT
    products = products_domain_qry_srv.get_products(project_id=project_id_value_object.from_str("proj-12345"))

    # ASSERT
    expected_products = [
        get_sample_product(),
        get_sample_product(product_id="prod-2"),
        get_sample_product(product_id="prod-3"),
        get_sample_product(product_id="prod-4"),
        get_sample_product(product_id="prod-5"),
    ]
    assertpy.assert_that(products).is_equal_to(expected_products)


@freeze_time("2023-07-07T00:00:00+00:00")
def test_get_product_by_id_returns_a_product(products_query_service_mock, versions_query_service_mock):
    # ARRANGE
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
    )

    # ACT
    p1, summaries = products_domain_qry_srv.get_product(
        project_id=project_id_value_object.from_str("proj-12345"), product_id=product_id_value_object.from_str("prod-1")
    )

    # ASSERT
    expected_product = product.Product(
        projectId="proj-12345",
        productId="prod-1",
        technologyId="tech-12345",
        technologyName="Test technology",
        status=product.ProductStatus.Created,
        productName="Product Name",
        productType=product.ProductType.Workbench,
        availableStages=[product.ProductStage.DEV],
        availableRegions=["us-east-1"],
        createDate=datetime.now(timezone.utc).isoformat(),
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        createdBy="T0012AB",
        lastUpdatedBy="T0012AB",
    )

    assertpy.assert_that(p1).is_equal_to(expected_product)


def test_get_product_by_id_returns_version_summaries(products_query_service_mock, versions_query_service_mock):
    # ARRANGE
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
    )

    # ACT
    p1, summaries = products_domain_qry_srv.get_product(
        project_id=project_id_value_object.from_str("proj-12345"), product_id=product_id_value_object.from_str("prod-1")
    )

    # ASSERT
    assertpy.assert_that(summaries).is_length(3)
    assertpy.assert_that(summaries).is_equal_to(
        [
            version_summary.VersionSummary(
                versionId="vers-123",
                name="1.0.0",
                description="Test Description",
                versionType=version.VersionType.Released.text,
                stages=[version.VersionStage.DEV],
                status=version_summary.VersionSummaryStatus.Created,
                recommendedVersion=True,
                lastUpdate="2000-01-01T00:00:00",
                lastUpdatedBy="T0011AA",
                restoredFromVersionName="1.0.0",
                originalAmiId="ami-123",
            ),
            version_summary.VersionSummary(
                versionId="v-000",
                name="2.0.0",
                description="Test Description",
                versionType=version.VersionType.Released.text,
                stages=[version.VersionStage.QA],
                status=version_summary.VersionSummaryStatus.Created,
                recommendedVersion=True,
                lastUpdate="2010-01-01T00:00:00",
                lastUpdatedBy="T0011AA",
                restoredFromVersionName="1.0.0",
                originalAmiId="ami-123",
            ),
            version_summary.VersionSummary(
                versionId="v-111",
                name="3.0.0",
                description="Test Description",
                versionType=version.VersionType.Released.text,
                stages=[version.VersionStage.PROD],
                status=version_summary.VersionSummaryStatus.Created,
                recommendedVersion=True,
                lastUpdate="2020-01-01T00:00:00",
                lastUpdatedBy="T0012AB",
                restoredFromVersionName="1.0.0",
                originalAmiId="ami-123",
            ),
        ]
    )


@pytest.mark.parametrize(
    "user_role,expected_product_count,allowed_stages",
    [
        pytest.param(VirtualWorkbenchRoles.PlatformUser.value, 2, [product.ProductStage.PROD]),
        pytest.param(VirtualWorkbenchRoles.BetaUser.value, 4, [product.ProductStage.PROD, product.ProductStage.QA]),
        pytest.param(
            VirtualWorkbenchRoles.ProductContributor.value,
            6,
            [product.ProductStage.PROD, product.ProductStage.QA, product.ProductStage.DEV],
        ),
    ],
)
def test_get_products_ready_for_provisioning_returns_correct_products_by_role(
    user_role,
    expected_product_count,
    allowed_stages: list[product.ProductStage],
    products_query_service_mock,
    versions_query_service_mock,
    get_sample_product,
):
    # ARRANGE
    sample_products = [
        get_sample_product(
            product_id="prod-5",
            available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
        ),
        get_sample_product(
            product_id="prod-6",
            available_stages=[product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD],
        ),
    ]
    if product.ProductStage.QA in allowed_stages:
        sample_products.extend(
            [
                get_sample_product(
                    product_id="prod-3", available_stages=[product.ProductStage.DEV, product.ProductStage.QA]
                ),
                get_sample_product(
                    product_id="prod-4", available_stages=[product.ProductStage.DEV, product.ProductStage.QA]
                ),
            ]
        )
    if product.ProductStage.DEV in allowed_stages:
        sample_products.extend([get_sample_product(), get_sample_product(product_id="prod-2")])

    products_query_service_mock.get_products.return_value = sample_products
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
    )

    # ACT
    products = products_domain_qry_srv.get_products_ready_for_provisioning(
        project_id=project_id_value_object.from_str("proj-12345"),
        user_roles=[user_role_value_object.from_str(user_role)],
        product_type=product_type_value_object.from_str("Workbench"),
    )

    # ASSERT
    assertpy.assert_that(products).is_length(expected_product_count)
    [assertpy.assert_that(allowed_stages).contains(stage) for prod in products for stage in prod.availableStages]
