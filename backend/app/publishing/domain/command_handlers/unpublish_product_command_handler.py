import functools
import logging
from datetime import datetime, timezone
from typing import Mapping

from app.publishing.domain.commands import unpublish_product_command
from app.publishing.domain.events import product_unpublished
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import catalog_query_service, catalog_service, versions_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.utils import async_io


def handle(
    cmd: unpublish_product_command.UnpublishProductCommand,
    uow: unit_of_work.UnitOfWork,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    catalog_srv: catalog_service.CatalogService,
    logger: logging.Logger,
    msg_bus: message_bus.MessageBus,
) -> None:
    """
    This command handler unpublishes a product.
    """
    try:
        with uow:
            # Get product entity
            product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
                pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value),
            )

            # Get versions of product
            versions = versions_qry_srv.get_product_version_distributions(product_id=cmd.productId.value)

            # Obtain unique set of sc product ids
            sc_products = functools.reduce(_sc_product_reducer, versions, {})

            # Loop through service catalog products and delete each if exists
            delete_product_responses = async_io.run_concurrently(
                *[
                    _delete_sc_product(
                        catalog_qry_srv=catalog_qry_srv,
                        catalog_srv=catalog_srv,
                        region=sc_product_dict["region"],
                        sc_product_id=sc_product_id,
                        sc_portfolio_id=sc_product_dict["scPortfolioId"],
                    )
                    for sc_product_id, sc_product_dict in sc_products.items()
                ]
            )

            # Raise exception in case of any
            error = next(iter([err for err in delete_product_responses if isinstance(err, Exception)]), None)
            if error:
                raise error

            # Loop through version distributions and mark each as retired
            commit_counter = 0
            for version_entity in versions:
                # Set version as retired
                uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                    pk=version.VersionPrimaryKey(
                        productId=version_entity.productId,
                        versionId=version_entity.versionId,
                        awsAccountId=version_entity.awsAccountId,
                    ),
                    status=version.VersionStatus.Retired,
                    lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                    lastUpdatedBy=product_entity.lastUpdatedBy,
                    retireReason="Product is archived",
                )
                commit_counter += 1
                if commit_counter % 10 == 0:  # Commit in batches of 10
                    uow.commit()
            # Commit remaining versions
            if commit_counter % 10 != 0:
                uow.commit()

            # Update product as archived
            uow.get_repository(product.ProductPrimaryKey, product.Product).update_attributes(
                pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value),
                status=product.ProductStatus.Archived,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

        # Publish event
        msg_bus.publish(
            product_unpublished.ProductUnpublished(
                projectId=cmd.projectId.value,
                productId=cmd.productId.value,
            )
        )

    except Exception as e:
        logger.exception("Failed to unpublish product")

        with uow:
            uow.get_repository(product.ProductPrimaryKey, product.Product).update_attributes(
                pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value),
                status=product.ProductStatus.Failed,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

        raise domain_exception.DomainException("Failed to unpublish product") from e


def _sc_product_reducer(prev: Mapping[str, dict], curr: version.Version) -> Mapping[str, dict]:
    prev[curr.scProductId] = {
        "scProductId": curr.scProductId,
        "scPortfolioId": curr.scPortfolioId,
        "region": curr.region,
    }
    return prev


async def _delete_sc_product(
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    catalog_srv: catalog_service.CatalogService,
    region: str,
    sc_product_id: str,
    sc_portfolio_id: str,
):
    # Check if the product exists
    if sc_product_id and catalog_qry_srv.does_product_exist_in_sc(region=region, sc_product_id=sc_product_id):
        # Disassociate product from portfolio
        catalog_srv.disassociate_product_from_portfolio(
            region=region,
            sc_portfolio_id=sc_portfolio_id,
            sc_product_id=sc_product_id,
        )

        # Delete product in service catalog
        catalog_srv.delete_product(region=region, sc_product_id=sc_product_id)
