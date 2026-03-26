import logging
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import copy_ami_command_handler
from app.publishing.domain.commands import copy_ami_command
from app.publishing.domain.ports import image_service
from app.publishing.domain.read_models import ami
from app.publishing.domain.value_objects import ami_id_value_object, region_value_object


def sample_ami() -> ami.Ami:
    return ami.Ami(
        projectId="proj-12345",
        amiId="ami-12345",
        amiName="Great AMI",
        amiDescription="This AMI is great",
        createDate="2023-07-25T00:00:00+00:00",
        lastUpdateDate="2023-07-25T00:00:00+00:00",
    )


@pytest.fixture()
def command_mock() -> copy_ami_command.CopyAmiCommand:
    return copy_ami_command.CopyAmiCommand(
        originalAmiId=ami_id_value_object.from_str("ami-12345"),
        region=region_value_object.from_str("eu-west-3"),
    )


@pytest.fixture
def image_service_mock():
    img_srv_mock = mock.create_autospec(spec=image_service.ImageService)
    img_srv_mock.copy_ami.return_value = "ami-54321"
    return img_srv_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@freeze_time("2023-07-25")
def test_copy_ami_command_handler_copies_ami(
    mock_amis_repo, command_mock, mock_unit_of_work, image_service_mock, logger_mock
):
    # ARRANGE
    mock_amis_repo.get.return_value = sample_ami()
    # ACT
    copied_ami_id = copy_ami_command_handler.handle(
        cmd=command_mock, uow=mock_unit_of_work, img_srv=image_service_mock, logger=logger_mock
    )

    # ASSERT
    image_service_mock.copy_ami.assert_called_once_with(
        region="eu-west-3",
        original_ami_id="ami-12345",
        ami_name="Great AMI",
        ami_description="This AMI is great",
    )
    assertpy.assert_that(copied_ami_id).is_equal_to("ami-54321")
