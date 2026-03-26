import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import create_portfolio_command
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio
from app.publishing.domain.ports import catalog_query_service, catalog_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: create_portfolio_command.CreatePortfolioCommand,
    uow: unit_of_work.UnitOfWork,
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    catalog_srv: catalog_service.CatalogService,
    logger: logging.Logger,
    main_account_roles: set[str],
    spoke_account_roles: set[str],
) -> None:
    portf = None
    portfolio_name = f"portfolio-{cmd.technologyId.value}-{cmd.awsAccountId.value}"

    logger.debug(f"Creating portfolio {portfolio_name}.")
    try:
        # Query repository to see if we created a portfolio for this account before by aws account and technology Id
        with uow:
            portf = uow.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio).get(
                pk=portfolio.PortfolioPrimaryKey(
                    technologyId=cmd.technologyId.value,
                    awsAccountId=cmd.awsAccountId.value,
                )
            )

        # Create the portfolio entity if it does not exist
        if not portf:
            current_time = datetime.now(timezone.utc).isoformat()
            portf = portfolio.Portfolio(
                projectId=cmd.projectId.value,
                technologyId=cmd.technologyId.value,
                awsAccountId=cmd.awsAccountId.value,
                accountId=cmd.accountId.value,
                stage=portfolio.PortfolioStage(cmd.stage.value),
                region=cmd.region.value,
                status=portfolio.PortfolioStatus.Creating,
                scPortfolioName=portfolio_name,
                createDate=current_time,
                lastUpdateDate=current_time,
            )
            with uow:
                uow.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio).add(portf)
                uow.commit()

        # Check if service catalog portfolio was already created
        sc_port_created = False
        if portf.scPortfolioId:
            sc_port_created = catalog_qry_srv.does_portfolio_exist_in_sc(
                region=cmd.region.value, sc_portfolio_id=portf.scPortfolioId
            )

        # If not created create the portfolio and store sc portfolio id
        if not sc_port_created:
            portf.scPortfolioId = catalog_srv.create_portfolio(
                region=cmd.region.value,
                portfolio_id=portf.portfolioId,
                portfolio_name=portfolio_name,
                portfolio_provider="Product Development Team",
            )
            with uow:
                uow.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio).update_attributes(
                    pk=portfolio.PortfolioPrimaryKey(
                        technologyId=cmd.technologyId.value,
                        awsAccountId=cmd.awsAccountId.value,
                    ),
                    scPortfolioId=portf.scPortfolioId,
                    lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                )
                uow.commit()

        # Share the portfolio with the use case account
        catalog_srv.share_portfolio(
            region=cmd.region.value, sc_portfolio_id=portf.scPortfolioId, aws_account_id=cmd.awsAccountId.value
        )

        # Accept the shared portfolio from user case account
        catalog_srv.accept_portfolio_share(
            region=cmd.region.value, sc_portfolio_id=portf.scPortfolioId, aws_account_id=cmd.awsAccountId.value
        )

        # Assign main account roles to portfolio
        __assign_service_catalog_roles(
            portf=portf,
            catalog_srv=catalog_srv,
            required_roles=main_account_roles,
        )

        # Assign spoke account roles to portfolio
        __assign_service_catalog_roles(
            portf=portf, catalog_srv=catalog_srv, required_roles=spoke_account_roles, is_spoke_account=True
        )

        # Update the status
        with uow:
            uow.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio).update_attributes(
                pk=portfolio.PortfolioPrimaryKey(
                    technologyId=cmd.technologyId.value,
                    awsAccountId=cmd.awsAccountId.value,
                ),
                status=portfolio.PortfolioStatus.Created,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                accountId=cmd.accountId.value,
            )
            uow.commit()
    except Exception as e:
        logger.error(f"Failed to create the portfolio. Error: {e}")
        if portf:
            with uow:
                uow.get_repository(portfolio.PortfolioPrimaryKey, portfolio.Portfolio).update_attributes(
                    pk=portfolio.PortfolioPrimaryKey(
                        technologyId=cmd.technologyId.value,
                        awsAccountId=cmd.awsAccountId.value,
                    ),
                    status=portfolio.PortfolioStatus.Failed,
                    lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                )
                uow.commit()
        raise domain_exception.DomainException("Failed to create the portfolio.") from e


def __assign_service_catalog_roles(
    portf: portfolio.Portfolio,
    catalog_srv: catalog_service.CatalogService,
    required_roles: set[str],
    is_spoke_account: bool = False,
):
    # Fetch existing portfolio roles
    existing_roles = set(
        catalog_srv.list_roles_for_portfolio(
            region=portf.region,
            sc_portfolio_id=portf.scPortfolioId,
            aws_account_id=portf.awsAccountId if is_spoke_account else None,
        )
    )

    # Remove non required roles from the portfolio
    non_required_roles = existing_roles - required_roles
    for non_required_role in non_required_roles:
        catalog_srv.disassociate_role_from_portfolio(
            region=portf.region,
            sc_portfolio_id=portf.scPortfolioId,
            role_name=non_required_role,
            aws_account_id=portf.awsAccountId if is_spoke_account else None,
        )

    # Add required roles to the portfolio
    missing_required_roles = required_roles - existing_roles
    for missing_required_role in missing_required_roles:
        catalog_srv.associate_role_with_portfolio(
            region=portf.region,
            sc_portfolio_id=portf.scPortfolioId,
            role_name=missing_required_role,
            aws_account_id=portf.awsAccountId if is_spoke_account else None,
        )
