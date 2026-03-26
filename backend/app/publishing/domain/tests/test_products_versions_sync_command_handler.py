import logging
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import products_versions_sync_command_handler
from app.publishing.domain.commands import products_versions_sync_command
from app.publishing.domain.events import product_availability_updated
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.publishing.domain.read_models import project
from app.publishing.domain.value_objects import project_id_value_object
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def get_version_mock():
    def _get_version_mock(
        product_id="prod-1",
        versionId="vers-12345abc",
    ):
        return version.Version(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            versionId=versionId,
            versionName="1.0.0-rc.2",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId="123456789012",
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            status=version.VersionStatus.Creating,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            draftTemplateLocation=f"prod-12345abc/{versionId}/workbench-template.yml",
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_version_mock


@pytest.fixture()
def get_product_mock():
    def _get_product_mock(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
        status=product.ProductStatus.Created.value,
        product_type=product.ProductType.Workbench,
    ):
        return product.Product(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            technologyName="Test technology",
            status=status,
            productName="Product Name",
            productType=product_type,
            availableStages=available_stages,
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )

    return _get_product_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def products_versions_sync_command_mock():
    products_versions_sync_command_mock = products_versions_sync_command.ProductsVersionsSyncCommand(
        projectId=project_id_value_object.from_str("pro-1234")
    )
    return products_versions_sync_command_mock


@pytest.fixture()
def versions_query_service_mock(get_version_mock):
    versions_query_service_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)

    def side_effect(product_id, statuses):
        return [get_version_mock(product_id, versionId=f"vers-dcm{idx}") for idx in range(10)]

    versions_query_service_mock.get_product_version_distributions.side_effect = side_effect
    return versions_query_service_mock


@pytest.fixture()
def products_query_service_mock():
    products_query_service_mock = mock.create_autospec(spec=products_query_service.ProductsQueryService)

    return products_query_service_mock


def get_project(project_id: str, project_name: str):
    return project.Project(
        projectId=project_id,
        projectName=project_name,
    )


@pytest.mark.parametrize(
    "projects",
    [
        [get_project(project_id="proj-12345", project_name="proj-A")],
    ],
)
@freeze_time("2023-09-01")
def test_handle_should_publish_product_availability_updated(
    projects,
    logger_mock,
    get_product_mock,
    products_versions_sync_command_mock,
    versions_query_service_mock,
    products_query_service_mock,
    projects_query_service_mock,
):
    # ARRANGE
    projects_query_service_mock.get_projects.return_value = projects
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    get_products_return_value_mocked = [
        get_product_mock(),
        get_product_mock(product_id="prod-2"),
    ]
    products_query_service_mock.get_products.return_value = get_products_return_value_mocked

    # ACT
    products_versions_sync_command_handler.handle(
        command=products_versions_sync_command_mock,
        versions_qry_srv=versions_query_service_mock,
        products_qry_service=products_query_service_mock,
        logger=logger_mock,
        message_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
    )

    # ASSERT
    expected_call_args_1 = product_availability_updated.ProductAvailabilityUpdated(
        projectId="proj-12345",
        productId="prod-1",
        productType=product.ProductType.Workbench,
        productName="Product Name",
        productDescription="",
        technologyId="tech-12345",
        technologyName="Test technology",
        availableStages=[product.ProductStage.DEV],
        availableRegions=["us-east-1"],
        lastUpdateDate="2023-09-01T00:00:00+00:00",
    )
    expected_call_args_2 = product_availability_updated.ProductAvailabilityUpdated(
        projectId="proj-12345",
        productId="prod-2",
        productType=product.ProductType.Workbench,
        productName="Product Name",
        productDescription="",
        technologyId="tech-12345",
        technologyName="Test technology",
        availableStages=[product.ProductStage.DEV],
        availableRegions=["us-east-1"],
        lastUpdateDate="2023-09-01T00:00:00+00:00",
    )

    message_bus_mock.publish.assert_has_calls(
        [
            mock.call(expected_call_args_1),
            mock.call(expected_call_args_2),
        ],
        any_order=True,
    )
