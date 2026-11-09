from unittest import mock

import assertpy
import pytest

from app.publishing.domain.command_handlers import create_license_grant_command_handler
from app.publishing.domain.exceptions.domain_exception import DomainException
from app.publishing.domain.model.marketplace_metadata import MarketplaceMetadata
from app.publishing.domain.ports import amis_query_service
from app.publishing.domain.read_models.license_grant_result import LicenseGrantResult


@pytest.fixture()
def mock_amis_qry_svc_for_grant():
    return mock.create_autospec(spec=amis_query_service.AMIsQueryService)


def test_handle_should_create_grant_when_valid(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
):
    # ARRANGE
    license_manager_service_mock.create_grant.return_value = LicenseGrantResult(
        grantArn="arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123",
        status="PENDING_ACCEPTANCE",
    )
    ami_mock = mock.Mock()
    ami_mock.marketplaceMetadata = MarketplaceMetadata(
        licenseConfigurationArn="arn:aws:license-manager:us-east-1:123456789012:license:l-abc123",
        productCode="abc123def456ghi",
    )
    mock_amis_qry_svc_for_grant.get_ami.return_value = ami_mock
    cmd = get_test_create_license_grant_command()

    # ACT
    result = create_license_grant_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        license_manager_service=license_manager_service_mock,
        msg_bus=mock_message_bus,
        amis_query_service=mock_amis_qry_svc_for_grant,
        logger=mock_logger,
    )

    # ASSERT
    assertpy.assert_that(result.grantId).starts_with("lg-")
    assertpy.assert_that(result.grantArn).is_equal_to("arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123")
    assertpy.assert_that(result.homeRegion).is_equal_to("us-east-1")
    license_manager_service_mock.create_grant.assert_called_once()
    mock_message_bus.publish.assert_called_once()


def test_handle_should_raise_when_no_license_arn(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
):
    # ARRANGE
    ami_mock = mock.Mock()
    ami_mock.marketplaceMetadata = MarketplaceMetadata(productCode="abc123def456ghi")
    mock_amis_qry_svc_for_grant.get_ami.return_value = ami_mock
    cmd = get_test_create_license_grant_command()

    # ACT
    with pytest.raises(DomainException, match="license configuration ARN") as exc_info:
        create_license_grant_command_handler.handle(
            command=cmd,
            uow=uow_mock,
            license_manager_service=license_manager_service_mock,
            msg_bus=mock_message_bus,
            amis_query_service=mock_amis_qry_svc_for_grant,
            logger=mock_logger,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("license configuration ARN")


def test_handle_should_use_license_arn_from_entity_metadata(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
):
    # ARRANGE
    license_manager_service_mock.create_grant.return_value = LicenseGrantResult(
        grantArn="arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123",
        status="PENDING_ACCEPTANCE",
    )
    entity_license_arn = "arn:aws:license-manager:us-east-1:123456789012:license:l-from-entity"
    ami_mock = mock.Mock()
    ami_mock.marketplaceMetadata = MarketplaceMetadata(licenseConfigurationArn=entity_license_arn)
    mock_amis_qry_svc_for_grant.get_ami.return_value = ami_mock
    cmd = get_test_create_license_grant_command()

    # ACT
    create_license_grant_command_handler.handle(
        command=cmd,
        uow=uow_mock,
        license_manager_service=license_manager_service_mock,
        msg_bus=mock_message_bus,
        amis_query_service=mock_amis_qry_svc_for_grant,
        logger=mock_logger,
    )

    # ASSERT
    call_kwargs = license_manager_service_mock.create_grant.call_args
    assertpy.assert_that(call_kwargs.kwargs["license_arn"]).is_equal_to(entity_license_arn)
