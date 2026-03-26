import logging
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import rename_version_distributions_command_handler
from app.publishing.domain.commands import rename_version_distributions_command
from app.publishing.domain.model import version
from app.publishing.domain.ports import catalog_service
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    version_id_value_object,
)


@pytest.fixture()
def get_version():
    def _get_version():
        return version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId="vers-12345abc",
            versionName="3.9.1",
            versionType=version.VersionType.Released.text,
            awsAccountId="123456789012",
            stage=version.VersionStage.QA,
            region="us-east-1",
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            status=version.VersionStatus.Updating,
            scPortfolioId="port-12345",
            scProductId="sc-prod-12345",
            scProvisioningArtifactId="sc-pa-12345",
            isRecommendedVersion=True,
            createDate="2023-10-06T00:00:00+00:00",
            lastUpdateDate="2023-10-06T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_version


@pytest.fixture()
def catalog_svc_mock():
    catalog_srv = mock.create_autospec(spec=catalog_service.CatalogService)
    return catalog_srv


@pytest.fixture()
def mock_command():
    mock_command = rename_version_distributions_command.RenameVersionDistributionsCommand(
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
    )
    return mock_command


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@freeze_time("2023-07-13")
def test_rename_version_command_handler_renames_provisioning_artifact_names(
    mock_command, mock_unit_of_work, catalog_svc_mock, mock_version_repo, logger_mock, get_version
):
    # ARRANGE
    mock_version_repo.get.return_value = get_version()
    catalog_svc_mock.update_provisioning_artifact_name.return_value = "AVAILABLE"

    # ACT
    rename_version_distributions_command_handler.handle(
        command=mock_command, uow=mock_unit_of_work, catalog_srv=catalog_svc_mock, logger=logger_mock
    )
    # ASSERT
    catalog_svc_mock.update_provisioning_artifact_name.assert_called_once_with(
        "us-east-1", "sc-prod-12345", "sc-pa-12345", "3.9.1"
    )
    mock_version_repo.update_attributes.assert_called_once_with(
        version.VersionPrimaryKey(
            productId="prod-12345abc",
            versionId="vers-12345abc",
            awsAccountId="123456789012",
        ),
        status=version.VersionStatus.Created.value,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
