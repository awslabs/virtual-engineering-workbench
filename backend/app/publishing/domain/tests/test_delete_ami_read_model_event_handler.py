import logging
from unittest import mock

import pytest

from app.publishing.domain.event_handlers import delete_ami_read_model_event_handler
from app.publishing.domain.read_models import ami
from app.publishing.domain.value_objects import ami_id_value_object


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


def test_delete_ami_read_model_event_handler_should_delete_ami(mock_amis_repo, mock_unit_of_work, logger_mock):
    # ARRANGE
    test_ami_id = "ami-12345"

    # ACT
    delete_ami_read_model_event_handler.handle(
        ami_id=ami_id_value_object.from_str(test_ami_id), uow=mock_unit_of_work, logger=logger_mock
    )

    # ASSERT
    mock_amis_repo.remove.assert_called_once_with(pk=ami.AmiPrimaryKey(amiId=test_ami_id))
    mock_unit_of_work.commit.assert_called_once()
