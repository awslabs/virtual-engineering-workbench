import tempfile
from unittest import mock

import assertpy
import pytest

from app.publishing.domain.model import product
from app.publishing.domain.ports import products_query_service, template_service, versions_query_service
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    version_id_value_object,
)


@pytest.fixture
def products_qry_srv_mock():
    return mock.create_autospec(spec=products_query_service.ProductsQueryService)


@pytest.fixture
def get_product():
    def _get_product(
        product_type: product.ProductType.Workbench = product.ProductType.Workbench,
        status: product.ProductStatus = product.ProductStatus.Created,
    ):
        return product.Product(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            technologyName="Test technology",
            status=status,
            productName="My product",
            productType=product_type,
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_product


@pytest.fixture
def versions_qry_srv_mock():
    versions_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    versions_qry_srv_mock.get_latest_version_name_and_id.return_value = "1.2.3", "vers-old"
    return versions_qry_srv_mock


@pytest.fixture
def template_srv_mock():
    template_srv_mock = mock.create_autospec(spec=template_service.TemplateService)
    return template_srv_mock


@pytest.mark.parametrize(
    "product_type_value, product_type",
    [
        ("workbench", product.ProductType.Workbench),
        ("virtual-target", product.ProductType.VirtualTarget),
        ("container", product.ProductType.Container),
    ],
)
def test_get_latest_template_for_case_1(
    products_qry_srv_mock, versions_qry_srv_mock, template_srv_mock, get_product, product_type_value, product_type
):
    # ARRANGE
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"Existing version template")
    temp_file.close()
    template_srv_mock.get_template.return_value = temp_file.name
    products_qry_srv_mock.get_product.return_value = get_product(product_type=product_type)
    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template="templates/workbench-template.yml",
        virtual_target_template="templates/virtual-target-template.yml",
        container_template="templates/container-template.yml",
        products_qry_srv=products_qry_srv_mock,
        template_srv=template_srv_mock,
        versions_qry_srv=versions_qry_srv_mock,
    )

    # ACT
    template = template_domain_qry_srv.get_latest_draft_template(
        project_id=project_id_value_object.from_str("proj-12345abc"),
        product_id=product_id_value_object.from_str("prod-12345abc"),
        version_id=version_id_value_object.from_str("vers-12345abc"),
    )

    # ASSERT
    assertpy.assert_that(template).is_equal_to("Existing version template")
    template_srv_mock.get_template.assert_called_once_with(
        template_path=f"prod-12345abc/vers-12345abc/draft-{product_type_value}-template.yml"
    )


@pytest.mark.parametrize(
    "product_type_value, product_type",
    [
        ("workbench", product.ProductType.Workbench),
        ("virtual-target", product.ProductType.VirtualTarget),
        ("container", product.ProductType.Container),
    ],
)
def test_get_latest_template_case_2(
    products_qry_srv_mock, versions_qry_srv_mock, template_srv_mock, get_product, product_type_value, product_type
):
    # ARRANGE
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"Latest version template")
    temp_file.close()
    template_srv_mock.get_template.return_value = temp_file.name
    products_qry_srv_mock.get_product.return_value = get_product(product_type=product_type)

    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template="templates/workbench-template.yml",
        virtual_target_template="templates/virtual-target-template.yml",
        container_template="templates/container-template.yml",
        products_qry_srv=products_qry_srv_mock,
        template_srv=template_srv_mock,
        versions_qry_srv=versions_qry_srv_mock,
    )

    # ACT
    template = template_domain_qry_srv.get_latest_draft_template(
        project_id=project_id_value_object.from_str("proj-12345abc"),
        product_id=product_id_value_object.from_str("prod-12345abc"),
    )

    # ASSERT
    assertpy.assert_that(template).is_equal_to("Latest version template")
    versions_qry_srv_mock.get_latest_version_name_and_id.assert_called_once_with(product_id="prod-12345abc")
    template_srv_mock.get_template.assert_called_once_with(
        template_path=f"prod-12345abc/vers-old/draft-{product_type_value}-template.yml"
    )


@pytest.mark.parametrize(
    "product_type_value, product_type",
    [
        ("workbench", product.ProductType.Workbench),
        ("virtual-target", product.ProductType.VirtualTarget),
        ("container", product.ProductType.Container),
    ],
)
def test_get_latest_template_case_3(
    products_qry_srv_mock, versions_qry_srv_mock, template_srv_mock, get_product, product_type_value, product_type
):
    # ARRANGE
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"Latest version template")
    temp_file.close()
    template_srv_mock.get_template.return_value = temp_file.name
    products_qry_srv_mock.get_product.return_value = get_product(product_type=product_type)
    versions_qry_srv_mock.get_latest_version_name_and_id.return_value = None, None
    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template="templates/workbench-template.yml",
        virtual_target_template="templates/virtual-target-template.yml",
        container_template="templates/container-template.yml",
        products_qry_srv=products_qry_srv_mock,
        template_srv=template_srv_mock,
        versions_qry_srv=versions_qry_srv_mock,
    )

    # ACT
    template = template_domain_qry_srv.get_latest_draft_template(
        project_id=project_id_value_object.from_str("proj-12345abc"),
        product_id=product_id_value_object.from_str("prod-12345abc"),
    )

    # ASSERT
    assertpy.assert_that(template).is_equal_to("Latest version template")
    versions_qry_srv_mock.get_latest_version_name_and_id.assert_called_once_with(product_id="prod-12345abc")
    template_srv_mock.get_template.assert_called_once_with(template_path=f"templates/{product_type_value}-template.yml")
