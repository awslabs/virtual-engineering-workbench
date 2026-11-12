from unittest import mock

import assertpy
import pytest

from app.publishing.domain.command_handlers import create_license_grant_command_handler
from app.publishing.domain.exceptions.domain_exception import DomainException
from app.publishing.domain.model.marketplace_metadata import MarketplaceMetadata
from app.publishing.domain.ports import amis_query_service, projects_query_service
from app.publishing.domain.read_models.license_grant_result import LicenseGrantResult
from app.publishing.domain.read_models.project_account import ProjectAccount

COMMAND_PROJECT_ID = "proj-123"
COMMAND_TARGET_ACCOUNT_ID = "999888777666"


@pytest.fixture()
def mock_amis_qry_svc_for_grant():
    return mock.create_autospec(spec=amis_query_service.AMIsQueryService)


@pytest.fixture()
def mock_projects_qry_svc_for_grant():
    svc = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    svc.get_aws_accounts_by_status.return_value = [
        ProjectAccount(id="pa-1", awsAccountId=COMMAND_TARGET_ACCOUNT_ID, stage="dev", region="us-east-1")
    ]
    return svc


def test_handle_should_create_grant_when_valid(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
    mock_projects_qry_svc_for_grant,
):
    # ARRANGE
    license_manager_service_mock.create_grant.return_value = LicenseGrantResult(
        grantArn="arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123",
        status="PENDING_ACCEPTANCE",
    )
    ami_mock = mock.Mock()
    ami_mock.projectId = COMMAND_PROJECT_ID
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
        projects_query_service=mock_projects_qry_svc_for_grant,
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
    mock_projects_qry_svc_for_grant,
):
    # ARRANGE
    ami_mock = mock.Mock()
    ami_mock.projectId = COMMAND_PROJECT_ID
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
            projects_query_service=mock_projects_qry_svc_for_grant,
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
    mock_projects_qry_svc_for_grant,
):
    # ARRANGE
    license_manager_service_mock.create_grant.return_value = LicenseGrantResult(
        grantArn="arn:aws:license-manager:us-east-1:123456789012:grant:g-abc123",
        status="PENDING_ACCEPTANCE",
    )
    entity_license_arn = "arn:aws:license-manager:us-east-1:123456789012:license:l-from-entity"
    ami_mock = mock.Mock()
    ami_mock.projectId = COMMAND_PROJECT_ID
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
        projects_query_service=mock_projects_qry_svc_for_grant,
        logger=mock_logger,
    )

    # ASSERT
    call_kwargs = license_manager_service_mock.create_grant.call_args
    assertpy.assert_that(call_kwargs.kwargs["license_arn"]).is_equal_to(entity_license_arn)


def test_handle_should_reject_an_ami_from_another_project(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
    mock_projects_qry_svc_for_grant,
):
    """Without this check a caller could have the hub distribute the licence of
    any AMI in the account, by naming a project they do have access to."""
    # ARRANGE
    ami_mock = mock.Mock()
    ami_mock.projectId = "proj-somebody-else"
    ami_mock.marketplaceMetadata = MarketplaceMetadata(
        licenseConfigurationArn="arn:aws:license-manager:us-east-1:123456789012:license:l-abc123",
    )
    mock_amis_qry_svc_for_grant.get_ami.return_value = ami_mock

    # ACT
    with pytest.raises(DomainException, match="is not part of project"):
        create_license_grant_command_handler.handle(
            command=get_test_create_license_grant_command(),
            uow=uow_mock,
            license_manager_service=license_manager_service_mock,
            msg_bus=mock_message_bus,
            amis_query_service=mock_amis_qry_svc_for_grant,
            projects_query_service=mock_projects_qry_svc_for_grant,
            logger=mock_logger,
        )

    # ASSERT
    license_manager_service_mock.create_grant.assert_not_called()
    mock_message_bus.publish.assert_not_called()


def test_handle_should_reject_an_unknown_ami(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
    mock_projects_qry_svc_for_grant,
):
    # ARRANGE
    mock_amis_qry_svc_for_grant.get_ami.return_value = None

    # ACT
    with pytest.raises(DomainException, match="is not part of project"):
        create_license_grant_command_handler.handle(
            command=get_test_create_license_grant_command(),
            uow=uow_mock,
            license_manager_service=license_manager_service_mock,
            msg_bus=mock_message_bus,
            amis_query_service=mock_amis_qry_svc_for_grant,
            projects_query_service=mock_projects_qry_svc_for_grant,
            logger=mock_logger,
        )

    # ASSERT
    license_manager_service_mock.create_grant.assert_not_called()


def test_handle_should_reject_a_target_account_outside_the_project(
    mock_logger,
    license_manager_service_mock,
    uow_mock,
    mock_message_bus,
    get_test_create_license_grant_command,
    mock_amis_qry_svc_for_grant,
    mock_projects_qry_svc_for_grant,
):
    """A grant hands a paid Marketplace licence to an AWS account, so the target
    has to be an active account of the project, not any account id."""
    # ARRANGE
    ami_mock = mock.Mock()
    ami_mock.projectId = COMMAND_PROJECT_ID
    ami_mock.marketplaceMetadata = MarketplaceMetadata(
        licenseConfigurationArn="arn:aws:license-manager:us-east-1:123456789012:license:l-abc123",
    )
    mock_amis_qry_svc_for_grant.get_ami.return_value = ami_mock
    mock_projects_qry_svc_for_grant.get_aws_accounts_by_status.return_value = [
        ProjectAccount(id="pa-2", awsAccountId="111111111111", stage="dev", region="us-east-1")
    ]

    # ACT
    with pytest.raises(DomainException, match="is not an active account of project"):
        create_license_grant_command_handler.handle(
            command=get_test_create_license_grant_command(),
            uow=uow_mock,
            license_manager_service=license_manager_service_mock,
            msg_bus=mock_message_bus,
            amis_query_service=mock_amis_qry_svc_for_grant,
            projects_query_service=mock_projects_qry_svc_for_grant,
            logger=mock_logger,
        )

    # ASSERT
    license_manager_service_mock.create_grant.assert_not_called()
    mock_message_bus.publish.assert_not_called()
