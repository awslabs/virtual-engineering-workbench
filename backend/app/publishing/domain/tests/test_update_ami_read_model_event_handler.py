import logging
import unittest
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.event_handlers import update_ami_read_model_event_handler
from app.publishing.domain.read_models import ami, component_version_detail


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def get_test_ami():
    def _get_test_ami(
        ami_id: str = "ami-1",
    ) -> ami.Ami:
        return ami.Ami(
            projectId="proj-12345",
            amiId=ami_id,
            amiName="Test Ami",
            amiDescription="Test Ami Description",
            componentVersionDetails=[
                component_version_detail.ComponentVersionDetail(
                    componentName="VS Code",
                    componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                    softwareVendor="Microsoft",
                    softwareVersion="1.87.0",
                )
            ],
            osVersion="Ubuntu 24",
            createDate="2024-03-06T00:00:00+00:00",
            lastUpdateDate="2024-03-06T00:00:00+00:00",
        )

    return _get_test_ami


@freeze_time("2024-03-06")
def test_update_ami_read_model_event_handler_retires_old_amis_and_inserts_new_ami(
    mock_amis_repo, mock_unit_of_work, logger_mock, get_test_ami
):
    # ARRANGE
    mock_amis_repo.get.side_effect = [
        get_test_ami("ami-1"),
        get_test_ami("ami-2"),
        get_test_ami("ami-3"),
    ]
    new_ami = get_test_ami("ami-4")

    # ACT
    update_ami_read_model_event_handler.handle(
        new_ami=new_ami,
        retired_ami_ids=["ami-1", "ami-2", "ami-3"],
        uow=mock_unit_of_work,
        logger=logger_mock,
    )

    # ASSERT
    mock_amis_repo.remove.assert_has_calls(
        [
            unittest.mock.call(pk=ami.AmiPrimaryKey(amiId="ami-1")),
            unittest.mock.call(pk=ami.AmiPrimaryKey(amiId="ami-2")),
            unittest.mock.call(pk=ami.AmiPrimaryKey(amiId="ami-3")),
        ]
    )
    mock_amis_repo.add.assert_called_once_with(new_ami)
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)


@freeze_time("2024-03-06")
def test_update_ami_read_model_event_handler_inserts_new_ami_when_there_is_no_ami_to_retire(
    mock_amis_repo, mock_unit_of_work, logger_mock, get_test_ami
):
    # ARRANGE
    mock_amis_repo.get.return_value = None
    new_ami = get_test_ami("ami-4")

    # ACT
    update_ami_read_model_event_handler.handle(
        new_ami=new_ami, retired_ami_ids=None, uow=mock_unit_of_work, logger=logger_mock
    )

    # ASSERT
    mock_amis_repo.remove.assert_not_called()
    mock_amis_repo.add.assert_called_once_with(new_ami)
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(1)
