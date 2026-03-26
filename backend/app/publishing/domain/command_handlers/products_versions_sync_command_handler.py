import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import products_versions_sync_command
from app.publishing.domain.events import product_availability_updated
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import products_query_service, projects_query_service, versions_query_service
from app.shared.adapters.message_bus import message_bus

PRODUCT_STAGE_SORT_ORDER = {
    product.ProductStage.DEV: 1,
    product.ProductStage.QA: 2,
    product.ProductStage.PROD: 3,
}


def handle(
    command: products_versions_sync_command.ProductsVersionsSyncCommand,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    products_qry_service: products_query_service.ProductsQueryService,
    logger: logging.Logger,
    message_bus: message_bus.MessageBus,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
) -> None:
    error_list: dict[str, Exception] = {}
    for project in projects_qry_srv.get_projects():
        logger.info(f"Sync for project: {project.projectName} - {project.projectId} started ...")
        products = products_qry_service.get_products(project.projectId)
        logger.info(f"Found {len(products)} in {project.projectName} program")
        created_products = [
            product_obj for product_obj in products if product_obj.status == product.ProductStatus.Created.value
        ]
        logger.info(f"Found {len(created_products)} 'Created' in {project.projectName} program")
        for product_obj in created_products:
            try:
                logger.info(f"Sync for product: {product_obj.productName} started ...")
                # Get created versions
                versions = versions_qry_srv.get_product_version_distributions(
                    product_id=product_obj.productId,
                    statuses=[version.VersionStatus.Created.value],
                )
                logger.info(f"Found {len(versions)} 'Created' versions for product {product_obj.productName}")

                # Get distinct set of stages and regions
                stages = set([product.ProductStage(v.stage) for v in versions])
                regions = set([v.region for v in versions])

                stages = sorted(stages, key=lambda s: PRODUCT_STAGE_SORT_ORDER[s])

                message_bus.publish(
                    product_availability_updated.ProductAvailabilityUpdated(
                        projectId=product_obj.projectId,
                        productId=product_obj.productId,
                        productType=product_obj.productType,
                        productName=product_obj.productName,
                        productDescription=(product_obj.productDescription if product_obj.productDescription else ""),
                        technologyId=product_obj.technologyId,
                        technologyName=product_obj.technologyName,
                        availableStages=stages,
                        availableRegions=sorted(regions),
                        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                    )
                )
            except Exception as e:
                error_list[product_obj.productId] = e
                logger.warning(f"Failed to update product availability for {product_obj.productId}")
    for e_product_id, e_from_list in error_list.items():
        logger.warning(
            f"Following product with product-id: {e_product_id}"
            f"throwed exception: {e_from_list} and was not able to publish ProductAvailabilityUpdated event!."
        )
