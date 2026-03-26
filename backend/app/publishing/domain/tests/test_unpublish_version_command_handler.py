import logging
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import unpublish_version_command_handler
from app.publishing.domain.commands import unpublish_version_command
from app.publishing.domain.events import product_version_unpublished
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import catalog_query_service, catalog_service
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    region_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus

TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"
TEST_VERSION_NAME = "1.0.0"


@pytest.fixture
def get_test_version():
    def _get_test_version(
        version_id: str = TEST_VERSION_ID,
        status: version.VersionStatus = version.VersionStatus.Created,
        stage: version.VersionStage = version.VersionStage.DEV,
        version_name: str = TEST_VERSION_NAME,
        last_updated_date: str = "2000-01-01",
    ):
        return version.Version(
            projectId="proj-123",
            productId=TEST_PRODUCT_ID,
            technologyId="t-123",
            versionId=version_id,
            versionName=version_name,
            versionType=version.VersionType.Released.text,
            versionDescription="Test Description",
            awsAccountId="001234567890",
            stage=stage,
            region="us-east-1",
            originalAmiId="ami-123",
            copiedAmiId="ami-456",
            status=status,
            scPortfolioId="port-123",
            scProductId="prod-12345",
            scProvisioningArtifactId="vers-12345",
            isRecommendedVersion=True,
            createDate="2000-01-01",
            lastUpdateDate=last_updated_date,
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            integrations=["integration-12345", "integration-67890"],
        )

    return _get_test_version


@pytest.fixture()
def command_mock():
    return unpublish_version_command.UnpublishVersionCommand(
        productId=product_id_value_object.from_str("prod-123"),
        versionId=version_id_value_object.from_str("vers-123"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
        region=region_value_object.from_str("us-east-1"),
    )


@pytest.fixture()
def catalog_service_mock():
    service_mock = mock.create_autospec(spec=catalog_service.CatalogService)
    return service_mock


@pytest.fixture()
def catalog_qry_svr():
    qry_svr_mock = mock.create_autospec(spec=catalog_query_service.CatalogQueryService)
    qry_svr_mock.does_provisioning_artifact_exist_in_sc.return_value = True
    qry_svr_mock.get_provisioning_artifact_count_in_sc.return_value = 2
    return qry_svr_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@freeze_time("2023-07-13")
def test_unpublish_version_command_handler_unpublish_version(
    command_mock,
    get_test_version,
    catalog_service_mock,
    catalog_qry_svr,
    mock_unit_of_work,
    mock_version_repo,
    logger_mock,
    message_bus_mock,
):
    # ARRANGE
    mock_version_repo.get.return_value = get_test_version()

    # ACT
    unpublish_version_command_handler.handle(
        command=command_mock,
        uow=mock_unit_of_work,
        catalog_srv=catalog_service_mock,
        catalog_qry_srv=catalog_qry_svr,
        logger=logger_mock,
        msg_bus=message_bus_mock,
    )
    # ASSERT
    catalog_service_mock.delete_provisioning_artifact.assert_called_once_with("us-east-1", "prod-12345", "vers-12345")
    catalog_qry_svr.does_provisioning_artifact_exist_in_sc.assert_called_once_with(
        "us-east-1", "prod-12345", "vers-12345"
    )
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId="prod-123",
            versionId="vers-123",
            awsAccountId="123456789012",
        ),
        lastUpdateDate="2023-07-13T00:00:00+00:00",
        status=version.VersionStatus.Retired,
    )
    mock_unit_of_work.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once_with(
        product_version_unpublished.ProductVersionUnpublished(
            projectId="proj-123",
            productId="prod-123",
            versionId="vers-123",
            awsAccountId="123456789012",
            region="us-east-1",
            stage="DEV",
            amiId="ami-456",
            integrations=["integration-12345", "integration-67890"],
            hasIntegrations=True,
        )
    )


def test_unpublish_version_command_handler_change_version_status_to_failed_if_error(
    command_mock,
    catalog_service_mock,
    catalog_qry_svr,
    mock_unit_of_work,
    mock_version_repo,
    logger_mock,
    message_bus_mock,
):
    # ARRANGE
    catalog_service_mock.delete_provisioning_artifact.side_effect = Exception
    # ASSERT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        unpublish_version_command_handler.handle(
            command=command_mock,
            uow=mock_unit_of_work,
            catalog_srv=catalog_service_mock,
            catalog_qry_srv=catalog_qry_svr,
            logger=logger_mock,
            msg_bus=message_bus_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to("Failed to unpublish a version")
        mock_version_repo.update_attributes.assert_called_once_with(
            pk=version.VersionPrimaryKey(
                productId="prod-123",
                versionId="vers-123",
                awsAccountId="123456789012",
            ),
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            status=version.VersionStatus.Failed,
        )


@freeze_time("2023-07-13")
def test_unpublish_version_command_handler_deletes_sc_product_if_last_version(
    command_mock,
    get_test_version,
    catalog_service_mock,
    catalog_qry_svr,
    mock_unit_of_work,
    logger_mock,
    message_bus_mock,
    mock_version_repo,
):
    # ARRANGE
    mock_version_repo.get.return_value = get_test_version()
    catalog_qry_svr.get_provisioning_artifact_count_in_sc.return_value = 1

    # ACT
    unpublish_version_command_handler.handle(
        command=command_mock,
        uow=mock_unit_of_work,
        catalog_srv=catalog_service_mock,
        catalog_qry_srv=catalog_qry_svr,
        logger=logger_mock,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    catalog_service_mock.disassociate_product_from_portfolio.assert_called_once_with(
        "us-east-1", "port-123", "prod-12345"
    )
    catalog_service_mock.delete_product.assert_called_once_with("us-east-1", "prod-12345")
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId="prod-123",
            versionId="vers-123",
            awsAccountId="123456789012",
        ),
        lastUpdateDate="2023-07-13T00:00:00+00:00",
        status=version.VersionStatus.Retired,
    )
    mock_unit_of_work.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once_with(
        product_version_unpublished.ProductVersionUnpublished(
            projectId="proj-123",
            productId="prod-123",
            versionId="vers-123",
            awsAccountId="123456789012",
            region="us-east-1",
            stage="DEV",
            amiId="ami-456",
            integrations=["integration-12345", "integration-67890"],
            hasIntegrations=True,
        )
    )
