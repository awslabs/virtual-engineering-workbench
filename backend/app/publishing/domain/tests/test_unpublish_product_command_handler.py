import logging
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import unpublish_product_command_handler
from app.publishing.domain.commands import unpublish_product_command
from app.publishing.domain.events import product_unpublished
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import catalog_query_service, catalog_service, versions_query_service
from app.publishing.domain.value_objects import product_id_value_object, project_id_value_object
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def command_mock() -> unpublish_product_command.UnpublishProductCommand:
    return unpublish_product_command.UnpublishProductCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-12345abc"),
    )


@pytest.fixture()
def get_product():
    def _get_product():
        return product.Product(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName="My product",
            productType=product.ProductType.Workbench,
            createDate="2023-08-22T00:00:00+00:00",
            lastUpdateDate="2023-08-22T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_product


@pytest.fixture()
def get_test_version():
    def _get_test_version(
        aws_account_id: str = "123456789012",
        sc_portfolio_id: str = "port-12345",
        sc_product_id: str = "prod-12345",
        region: str = "us-east-1",
        version_id: str = "vers-12345abc",
    ):
        return version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId=version_id,
            versionName="2.3.4",
            versionType=version.VersionType.Released.text,
            awsAccountId=aws_account_id,
            stage=version.VersionStage.DEV,
            region=region,
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            status=version.VersionStatus.Created,
            scPortfolioId=sc_portfolio_id,
            scProductId=sc_product_id,
            scProvisioningArtifactId="pa-12345",
            isRecommendedVersion=True,
            createDate="2023-08-22T00:00:00+00:00",
            lastUpdateDate="2023-08-22T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_test_version


@pytest.fixture
def versions_query_service_mock(get_test_version):
    vers_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    vers_qry_srv_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(
            aws_account_id="123456789013",
            sc_portfolio_id="port-54321",
            sc_product_id="prod-54321",
            region="eu-west-3",
        ),
        get_test_version(aws_account_id="123456789014", version_id="vers-54321abc"),
    ]
    return vers_qry_srv_mock


@pytest.fixture()
def catalog_service_mock():
    catalog_srv_mock = mock.create_autospec(spec=catalog_service.CatalogService)
    catalog_srv_mock.disassociate_product_from_portfolio.return_value = None
    catalog_srv_mock.delete_product.return_value = None
    return catalog_srv_mock


@pytest.fixture()
def catalog_query_service_mock():
    catalog_qry_srv_mock = mock.create_autospec(spec=catalog_query_service.CatalogQueryService)
    catalog_qry_srv_mock.does_product_exist_in_sc.return_value = True
    return catalog_qry_srv_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@freeze_time("2023-08-22")
def test_unpublish_product_command_handler_deletes_product_in_sc_if_exists(
    command_mock,
    mock_products_repo,
    mock_version_repo,
    mock_unit_of_work,
    versions_query_service_mock,
    catalog_query_service_mock,
    catalog_service_mock,
    logger_mock,
    message_bus_mock,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    # ACT
    unpublish_product_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        versions_qry_srv=versions_query_service_mock,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    catalog_service_mock.disassociate_product_from_portfolio.assert_has_calls(
        [
            mock.call(
                region="us-east-1",
                sc_portfolio_id="port-12345",
                sc_product_id="prod-12345",
            ),
            mock.call(
                region="eu-west-3",
                sc_portfolio_id="port-54321",
                sc_product_id="prod-54321",
            ),
        ]
    )
    catalog_service_mock.delete_product.assert_has_calls(
        [
            mock.call(
                region="us-east-1",
                sc_product_id="prod-12345",
            ),
            mock.call(
                region="eu-west-3",
                sc_product_id="prod-54321",
            ),
        ]
    )
    mock_version_repo.update_attributes.assert_has_calls(
        [
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789012",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789013",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-54321abc",
                    awsAccountId="123456789014",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
        ]
    )
    mock_products_repo.update_attributes.assert_called_with(
        pk=product.ProductPrimaryKey(
            projectId="proj-12345",
            productId="prod-12345abc",
        ),
        status=product.ProductStatus.Archived,
        lastUpdateDate="2023-08-22T00:00:00+00:00",
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_called_once_with(
        product_unpublished.ProductUnpublished(projectId="proj-12345", productId="prod-12345abc")
    )


@freeze_time("2023-08-22")
def test_unpublish_product_command_handler_only_updates_record_if_not_exist_in_sc(
    command_mock,
    mock_products_repo,
    mock_version_repo,
    mock_unit_of_work,
    versions_query_service_mock,
    catalog_query_service_mock,
    catalog_service_mock,
    logger_mock,
    message_bus_mock,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()
    catalog_query_service_mock.does_product_exist_in_sc.return_value = False

    # ACT
    unpublish_product_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        versions_qry_srv=versions_query_service_mock,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    catalog_service_mock.disassociate_product_from_portfolio.assert_not_called()
    catalog_service_mock.delete_product.assert_not_called()
    mock_version_repo.update_attributes.assert_has_calls(
        [
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789012",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789013",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-54321abc",
                    awsAccountId="123456789014",
                ),
                status=version.VersionStatus.Retired,
                lastUpdateDate="2023-08-22T00:00:00+00:00",
                lastUpdatedBy="T000001",
                retireReason="Product is archived",
            ),
        ]
    )
    mock_products_repo.update_attributes.assert_called_with(
        pk=product.ProductPrimaryKey(
            projectId="proj-12345",
            productId="prod-12345abc",
        ),
        status=product.ProductStatus.Archived,
        lastUpdateDate="2023-08-22T00:00:00+00:00",
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_called_once_with(
        product_unpublished.ProductUnpublished(projectId="proj-12345", productId="prod-12345abc")
    )
