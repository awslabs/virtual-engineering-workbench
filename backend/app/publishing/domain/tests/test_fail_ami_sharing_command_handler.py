import logging
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import fail_ami_sharing_command_handler
from app.publishing.domain.commands import fail_ami_sharing_command
from app.publishing.domain.model import version
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    version_id_value_object,
)


@pytest.fixture()
def command_mock() -> fail_ami_sharing_command.FailAmiSharingCommand:
    return fail_ami_sharing_command.FailAmiSharingCommand(
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
    )


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@freeze_time("2023-07-31")
def test_fail_ami_sharing_command_handler_updates_version_as_failed(
    command_mock, mock_unit_of_work, logger_mock, mock_version_repo
):
    # ARRANGE

    # ACT
    fail_ami_sharing_command_handler.handle(cmd=command_mock, uow=mock_unit_of_work, logger=logger_mock)

    # ASSERT
    mock_version_repo.update_attributes.assert_called_once_with(
        version.VersionPrimaryKey(productId="prod-12345abc", versionId="vers-12345abc", awsAccountId="123456789012"),
        status=version.VersionStatus.Failed,
        lastUpdateDate="2023-07-31T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
