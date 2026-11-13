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
    license_manager_service_mock.accept_grant.assert_not_called()
    mock_message_bus.publish.assert_not_called()


def test_handle_uses_persisted_grant_identity_instead_of_command_values(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_license_grant_entity,
    get_test_accept_license_grant_command,
):
    # ARRANGE — only projectId and grantId select the persisted record. The AWS
    # request and event must not trust the remaining command-supplied values.
    grant_entity = get_test_license_grant_entity(
        grantArn="arn:aws:license-manager:eu-west-1:123456789012:grant:g-persisted",
        homeRegion="eu-west-1",
        targetAccountId="111122223333",
    )
    uow_mock.get_repository.return_value.get.return_value = grant_entity
    cmd = get_test_accept_license_grant_command(
        grant_arn="arn:aws:license-manager:ap-southeast-1:123456789012:grant:g-command",
        home_region="ap-southeast-1",
        target_account_id="444455556666",
    )

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
        grant_arn="arn:aws:license-manager:eu-west-1:123456789012:grant:g-persisted",
        home_region="eu-west-1",
        spoke_account_id="111122223333",
    )
    event = mock_message_bus.publish.call_args.args[0]
    assertpy.assert_that(event.grant_id).is_equal_to(grant_entity.grantId)
    assertpy.assert_that(event.grant_arn).is_equal_to(grant_entity.grantArn)
    assertpy.assert_that(event.target_account_id).is_equal_to(grant_entity.targetAccountId)
    assertpy.assert_that(grant_entity.status.value).is_equal_to("ACTIVE")
