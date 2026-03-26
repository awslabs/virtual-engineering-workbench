import logging
from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest

from app.publishing.domain.command_handlers import create_portfolio_command_handler
from app.publishing.domain.commands import create_portfolio_command
from app.publishing.domain.model import portfolio
from app.publishing.domain.ports import catalog_query_service, catalog_service
from app.publishing.domain.value_objects import (
    account_id_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
    stage_value_object,
    tech_id_value_object,
)

TEST_SC_PORTFOLIO_ID = "port-12345"
MAIN_ACCOUNT_ROLES = {"ProductPublishingAdminRole"}
SPOKE_ACCOUNT_ROLES = {"WorkbenchWebAppProvisioningRoleV2", "WorkbenchCatalogAccessRole"}


@pytest.fixture()
def command_mock() -> create_portfolio_command.CreatePortfolioCommand:
    return create_portfolio_command.CreatePortfolioCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        technologyId=tech_id_value_object.from_str("tech-12345"),
        awsAccountId=aws_account_id_value_object.from_str("123456789012"),
        accountId=account_id_value_object.from_str("1d0b2901-9482-4ce5-9d91-582fe0b14d7b"),
        stage=stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
    )


def list_roles_for_portfolio_side_effect(*args, **kwargs):
    if kwargs["aws_account_id"]:
        return list(SPOKE_ACCOUNT_ROLES)
    return list(MAIN_ACCOUNT_ROLES)


def list_roles_for_portfolio_side_effect_wrong_acct(*args, **kwargs):
    if kwargs["aws_account_id"]:
        accounts = list(SPOKE_ACCOUNT_ROLES)
        accounts.append("RandomRole")
        return accounts
    return list(MAIN_ACCOUNT_ROLES)


@pytest.fixture()
def catalog_service_mock():
    catalog_srv_mock = mock.create_autospec(spec=catalog_service.CatalogService)
    catalog_srv_mock.create_portfolio.return_value = TEST_SC_PORTFOLIO_ID
    catalog_srv_mock.share_portfolio.return_value = None
    catalog_srv_mock.accept_portfolio_share.return_value = None
    catalog_srv_mock.associate_role_with_portfolio.return_value = None
    catalog_srv_mock.disassociate_role_from_portfolio.return_value = None
    catalog_srv_mock.list_roles_for_portfolio.return_value = []
    return catalog_srv_mock


@pytest.fixture()
def catalog_query_service_mock():
    catalog_qry_srv_mock = mock.create_autospec(spec=catalog_query_service.CatalogQueryService)
    return catalog_qry_srv_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def mocked_portfolio(command_mock):
    current_time = datetime.now(timezone.utc).isoformat()
    return portfolio.Portfolio(
        portfolioId="port-12345abc",
        projectId=command_mock.projectId.value,
        technologyId=command_mock.technologyId.value,
        awsAccountId=command_mock.awsAccountId.value,
        stage=portfolio.PortfolioStage(command_mock.stage.value),
        region=command_mock.region.value,
        status=portfolio.PortfolioStatus.Creating,
        scPortfolioId=TEST_SC_PORTFOLIO_ID,
        scPortfolioName=f"{command_mock.technologyId.value}-{command_mock.awsAccountId.value}",
        createDate=current_time,
        lastUpdateDate=current_time,
    )


def test_create_portfolio_command_handler_should_create_portfolio_when_does_not_exist(
    command_mock, catalog_service_mock, catalog_query_service_mock, logger_mock, mock_unit_of_work, mock_portfolio_repo
):
    # ARRANGE
    mock_portfolio_repo.get.return_value = None
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = False

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.create_portfolio.assert_called_once()
    catalog_service_mock.share_portfolio.assert_called_once()
    catalog_service_mock.accept_portfolio_share.assert_called_once()
    assertpy.assert_that(catalog_service_mock.associate_role_with_portfolio.call_count).is_equal_to(3)
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(3)
    mock_portfolio_repo.update_attributes.assert_called_with(
        pk=portfolio.PortfolioPrimaryKey(
            technologyId=command_mock.technologyId.value, awsAccountId=command_mock.awsAccountId.value
        ),
        status=portfolio.PortfolioStatus.Created,
        lastUpdateDate=mock_portfolio_repo.update_attributes.call_args.kwargs["lastUpdateDate"],
        accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
    )


def test_create_portfolio_command_handler_should_not_create_portfolio_if_exists(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_portfolio_repo,
    mocked_portfolio,
):
    # ARRANGE
    mock_portfolio_repo.get.return_value = mocked_portfolio
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = True

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.create_portfolio.assert_not_called()
    catalog_service_mock.share_portfolio.assert_called_once()
    catalog_service_mock.accept_portfolio_share.assert_called_once()
    assertpy.assert_that(catalog_service_mock.associate_role_with_portfolio.call_count).is_equal_to(3)
    mock_unit_of_work.commit.assert_called_once()
    mock_portfolio_repo.update_attributes.assert_called_once_with(
        pk=portfolio.PortfolioPrimaryKey(
            technologyId=command_mock.technologyId.value, awsAccountId=command_mock.awsAccountId.value
        ),
        status=portfolio.PortfolioStatus.Created,
        lastUpdateDate=mock_portfolio_repo.update_attributes.call_args.kwargs["lastUpdateDate"],
        accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
    )


def test_create_portfolio_command_handler_should_create_portfolio_if_exists_in_repo_but_not_in_sc(
    command_mock, mock_unit_of_work, catalog_service_mock, catalog_query_service_mock, logger_mock, mock_portfolio_repo
):
    # ARRANGE
    current_time = datetime.now(timezone.utc).isoformat()
    mock_portfolio_repo.get.return_value = portfolio.Portfolio(
        portfolioId="port-12345abc",
        projectId=command_mock.projectId.value,
        technologyId=command_mock.technologyId.value,
        awsAccountId=command_mock.awsAccountId.value,
        stage=portfolio.PortfolioStage(command_mock.stage.value),
        region=command_mock.region.value,
        status=portfolio.PortfolioStatus.Creating,
        scPortfolioId=TEST_SC_PORTFOLIO_ID,
        scPortfolioName=f"{command_mock.technologyId.value}-{command_mock.awsAccountId.value}",
        createDate=current_time,
        lastUpdateDate=current_time,
    )
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = False

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.create_portfolio.assert_called_once()
    catalog_service_mock.share_portfolio.assert_called_once()
    catalog_service_mock.accept_portfolio_share.assert_called_once()
    assertpy.assert_that(catalog_service_mock.associate_role_with_portfolio.call_count).is_equal_to(3)
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    mock_portfolio_repo.update_attributes.assert_called_with(
        pk=portfolio.PortfolioPrimaryKey(
            technologyId=command_mock.technologyId.value, awsAccountId=command_mock.awsAccountId.value
        ),
        status=portfolio.PortfolioStatus.Created,
        lastUpdateDate=mock_portfolio_repo.update_attributes.call_args.kwargs["lastUpdateDate"],
        accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
    )


def test_create_portfolio_when_required_role_is_not_associated_should_associate(
    command_mock,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_unit_of_work,
    mock_portfolio_repo,
    mocked_portfolio,
):
    # ARRANGE
    mock_portfolio_repo.get.return_value = mocked_portfolio
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = True

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.associate_role_with_portfolio.assert_has_calls(
        [
            mock.call(
                region=command_mock.region.value,
                sc_portfolio_id=mocked_portfolio.scPortfolioId,
                role_name=MAIN_ACCOUNT_ROLES.pop(),
                aws_account_id=None,
            ),
            mock.call(
                region=command_mock.region.value,
                sc_portfolio_id=mocked_portfolio.scPortfolioId,
                role_name=SPOKE_ACCOUNT_ROLES.pop(),
                aws_account_id=command_mock.awsAccountId.value,
            ),
            mock.call(
                region=command_mock.region.value,
                sc_portfolio_id=mocked_portfolio.scPortfolioId,
                role_name=SPOKE_ACCOUNT_ROLES.pop(),
                aws_account_id=command_mock.awsAccountId.value,
            ),
        ],
        any_order=True,
    )


def test_create_portfolio_when_required_role_is_associated_should_not_associate(
    command_mock,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_unit_of_work,
    mock_portfolio_repo,
    mocked_portfolio,
):
    # ARRANGE
    mock_portfolio_repo.get.return_value = mocked_portfolio
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = True
    catalog_service_mock.list_roles_for_portfolio.side_effect = list_roles_for_portfolio_side_effect

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.disassociate_role_from_portfolio.assert_not_called()
    catalog_service_mock.associate_role_with_portfolio.assert_not_called()


def test_create_portfolio_should_clean_non_required_roles(
    command_mock,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_unit_of_work,
    mock_portfolio_repo,
    mocked_portfolio,
):
    # ARRANGE
    mock_portfolio_repo.get.return_value = mocked_portfolio
    catalog_query_service_mock.does_portfolio_exist_in_sc.return_value = True
    catalog_service_mock.list_roles_for_portfolio.side_effect = list_roles_for_portfolio_side_effect_wrong_acct

    # ACT
    create_portfolio_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        main_account_roles=MAIN_ACCOUNT_ROLES,
        spoke_account_roles=SPOKE_ACCOUNT_ROLES,
    )

    # ASSERT
    catalog_service_mock.disassociate_role_from_portfolio.assert_called_once_with(
        region=command_mock.region.value,
        sc_portfolio_id=mocked_portfolio.scPortfolioId,
        aws_account_id=command_mock.awsAccountId.value,
        role_name="RandomRole",
    )
