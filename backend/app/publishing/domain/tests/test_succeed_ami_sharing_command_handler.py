import logging
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import succeed_ami_sharing_command_handler
from app.publishing.domain.commands import succeed_ami_sharing_command
from app.publishing.domain.events import product_version_ami_shared
from app.publishing.domain.model import version
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    product_type_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def command_mock() -> succeed_ami_sharing_command.SucceedAmiSharingCommand:
    return succeed_ami_sharing_command.SucceedAmiSharingCommand(
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
        copiedAmiId=ami_id_value_object.from_str("ami-54321"),
        previousEventName=event_name_value_object.from_str("ProductVersionCreationStarted"),
        productType=product_type_value_object.from_str("WORKBENCH"),
    )


@pytest.fixture()
def command_mock_container_type() -> succeed_ami_sharing_command.SucceedAmiSharingCommand:
    return succeed_ami_sharing_command.SucceedAmiSharingCommand(
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
        copiedAmiId=None,
        previousEventName=event_name_value_object.from_str("ProductVersionCreationStarted"),
        productType=product_type_value_object.from_str("CONTAINER"),
    )


@pytest.fixture
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@freeze_time("2023-07-31")
def test_succeed_ami_sharing_command_handler_updates_version_and_publishes_event(
    command_mock, mock_unit_of_work, message_bus_mock, logger_mock, mock_version_repo
):
    # ARRANGE

    # ACT
    succeed_ami_sharing_command_handler.handle(
        cmd=command_mock, uow=mock_unit_of_work, msg_bus=message_bus_mock, logger=logger_mock
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_called_once_with(
        version.VersionPrimaryKey(productId="prod-12345abc", versionId="vers-12345abc", awsAccountId="123456789012"),
        copiedAmiId="ami-54321",
        lastUpdateDate="2023-07-31T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once_with(
        product_version_ami_shared.ProductVersionAmiShared(
            product_id="prod-12345abc",
            version_id="vers-12345abc",
            aws_account_id="123456789012",
            previousEventName="ProductVersionCreationStarted",
        )
    )


@freeze_time("2023-07-31")
def test_succeed_ami_sharing_command_handler_doesnt_update_version_and_publishes_event_on_container_product_type(
    command_mock_container_type, mock_unit_of_work, message_bus_mock, logger_mock, mock_version_repo
):
    # ARRANGE

    # ACT
    succeed_ami_sharing_command_handler.handle(
        cmd=command_mock_container_type, uow=mock_unit_of_work, msg_bus=message_bus_mock, logger=logger_mock
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_ami_shared.ProductVersionAmiShared(
            product_id="prod-12345abc",
            version_id="vers-12345abc",
            aws_account_id="123456789012",
            previousEventName="ProductVersionCreationStarted",
        )
    )
