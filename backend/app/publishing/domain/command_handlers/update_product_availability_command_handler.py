import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import update_product_availability_command
from app.publishing.domain.events import product_availability_updated
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import versions_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

PRODUCT_STAGE_SORT_ORDER = {
    product.ProductStage.DEV: 1,
    product.ProductStage.QA: 2,
    product.ProductStage.PROD: 3,
}


def handle(
    command: update_product_availability_command.UpdateProductAvailabilityCommand,
    uow: unit_of_work.UnitOfWork,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    logger: logging.Logger,
    message_bus: message_bus.MessageBus,
) -> None:
    try:
        # Get version distributions in processing states
        processing_versions = versions_qry_srv.get_product_version_distributions(
            product_id=command.productId.value, statuses=version.VersionStatus.get_processing_statuses()
        )

        # If there is a version which is currently being processed, we skip executing the command
        # This command will be executed again once the processing of other version finishes
        # This way we don't publish duplicate events
        if processing_versions:
            logger.warning(
                "There are still some version distributions being processed. Skipping updating the product availability until they are finished."
            )
            return

        # Get created versions
        versions = versions_qry_srv.get_product_version_distributions(
            product_id=command.productId.value, statuses=[version.VersionStatus.Created]
        )

        # Get distinct set of stages and regions
        stages = set()
        regions = set()
        for vers in versions:
            stages.add(product.ProductStage(vers.stage))
            regions.add(vers.region)
        stages = sorted(stages, key=lambda s: PRODUCT_STAGE_SORT_ORDER[s])

        # Update product
        with uow:
            product_repo = uow.get_repository(product.ProductPrimaryKey, product.Product)
            product_repo.update_attributes(
                pk=product.ProductPrimaryKey(
                    projectId=command.projectId.value,
                    productId=command.productId.value,
                ),
                availableStages=stages,
                availableRegions=list(regions),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

            product_entity = product_repo.get(
                pk=product.ProductPrimaryKey(
                    projectId=command.projectId.value,
                    productId=command.productId.value,
                )
            )

        message_bus.publish(
            product_availability_updated.ProductAvailabilityUpdated(
                projectId=product_entity.projectId,
                productId=product_entity.productId,
                productType=product_entity.productType,
                productName=product_entity.productName,
                productDescription=product_entity.productDescription,
                technologyId=product_entity.technologyId,
                technologyName=product_entity.technologyName,
                availableStages=stages,
                availableRegions=sorted(regions),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
        )
    except Exception as e:
        logger.exception("Failed to update product availability")
        raise domain_exception.DomainException("Failed to update product availability") from e
