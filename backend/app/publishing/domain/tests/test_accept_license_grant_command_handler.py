import assertpy
import pytest

from app.publishing.domain.command_handlers import accept_license_grant_command_handler
from app.publishing.domain.exceptions.domain_exception import DomainException


def test_handle_should_accept_grant_when_valid(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_license_grant_entity,
    get_test_accept_license_grant_command,
):
    # ARRANGE
    grant_entity = get_test_license_grant_entity()
    uow_mock.get_repository.return_value.get.return_value = grant_entity
    cmd = get_test_accept_license_grant_command()

    # ACT
    accept_license_grant_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        license_manager_service=license_manager_service_mock,
        msg_bus=mock_message_bus,
        logger=mock_logger,
    )

    # ASSERT
    license_manager_service_mock.accept_grant.assert_called_once_with(
        grant_arn="arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123",
        home_region="us-east-1",
        spoke_account_id="999888777666",
    )
    mock_message_bus.publish.assert_called_once()


def test_handle_should_raise_when_grant_not_found(
    mock_logger, license_manager_service_mock, uow_mock, mock_message_bus, get_test_accept_license_grant_command
):
    # ARRANGE
    uow_mock.get_repository.return_value.get.return_value = None
    cmd = get_test_accept_license_grant_command(
        grant_id="lg-notfound", grant_arn="arn:aws:license-manager:us-east-1:123456789012:grant:g-notfound"
    )

    # ACT
    with pytest.raises(DomainException, match="not found") as exc_info:
        accept_license_grant_command_handler.handle(
            command=cmd,
            uow=uow_mock,
            license_manager_service=license_manager_service_mock,
            msg_bus=mock_message_bus,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("not found")
