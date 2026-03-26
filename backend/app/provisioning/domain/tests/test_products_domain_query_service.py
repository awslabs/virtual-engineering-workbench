from unittest import mock

import assertpy
import pytest

from app.provisioning.domain.ports import products_query_service
from app.provisioning.domain.query_services import products_domain_query_service
from app.provisioning.domain.read_models import product
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_type_value_object,
    project_id_value_object,
    user_role_value_object,
)
from app.shared.middleware.authorization import VirtualWorkbenchRoles


@pytest.fixture()
def get_sample_product():
    def _get_sample_product(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
        product_type=product.ProductType.VirtualTarget,
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


@pytest.fixture()
def products_query_service_mock():
    products_qry_srv_mock = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    return products_qry_srv_mock


@pytest.mark.parametrize(
    "user_role,expected_product_count,allowed_stages",
    [
        pytest.param(VirtualWorkbenchRoles.PlatformUser.value, 2, [product.ProductStage.PROD]),
        pytest.param(
            VirtualWorkbenchRoles.BetaUser.value,
            4,
            [product.ProductStage.PROD, product.ProductStage.QA],
        ),
        pytest.param(
            VirtualWorkbenchRoles.ProductContributor.value,
            6,
            [
                product.ProductStage.PROD,
                product.ProductStage.QA,
                product.ProductStage.DEV,
            ],
        ),
    ],
)
def test_get_available_products_returns_correct_products_by_role(
    user_role,
    expected_product_count,
    allowed_stages: list[product.ProductStage],
    products_query_service_mock,
    get_sample_product,
):
    # ARRANGE
    sample_products = [
        get_sample_product(
            product_id="prod-5",
            available_stages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
        ),
        get_sample_product(
            product_id="prod-6",
            available_stages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
        ),
    ]
    if product.ProductStage.QA in allowed_stages:
        sample_products.extend(
            [
                get_sample_product(
                    product_id="prod-3",
                    available_stages=[
                        product.ProductStage.DEV,
                        product.ProductStage.QA,
                    ],
                ),
                get_sample_product(
                    product_id="prod-4",
                    available_stages=[
                        product.ProductStage.DEV,
                        product.ProductStage.QA,
                    ],
                ),
            ]
        )
    if product.ProductStage.DEV in allowed_stages:
        sample_products.extend([get_sample_product(), get_sample_product(product_id="prod-2")])

    products_query_service_mock.get_products.return_value = sample_products
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        networking_qry_srv=mock.MagicMock(),
    )

    # ACT
    products = products_domain_qry_srv.get_available_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        user_roles=[user_role_value_object.from_str(user_role)],
        product_type=product_type_value_object.from_str("VirtualTarget"),
    )

    # ASSERT
    assertpy.assert_that(products).is_length(expected_product_count)
    [assertpy.assert_that(allowed_stages).contains(stage) for prod in products for stage in prod.availableStages]


def test_get_available_products_returns_filtered_list(products_query_service_mock, get_sample_product):
    # ARRANGE
    sample_products = [
        get_sample_product(
            product_id="prod-1",
            available_stages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
        ),
        get_sample_product(
            product_id="prod-2",
            available_stages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
        ),
    ]
    expected_product_ids = ["prod-1"]
    products_query_service_mock.get_products.return_value = sample_products
    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_query_service_mock,
        networking_qry_srv=mock.MagicMock(),
    )

    # ACT
    products = products_domain_qry_srv.get_available_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        user_roles=[user_role_value_object.from_str("ADMIN")],
        product_type=product_type_value_object.from_str("VirtualTarget"),
        product_id_filter=[product_id_value_object.from_str("prod-1")],
    )

    # ASSERT
    result_product_ids = [prod.productId for prod in products]
    assertpy.assert_that(result_product_ids).is_equal_to(expected_product_ids)
