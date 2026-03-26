from datetime import datetime, timezone

from app.publishing.domain.commands import archive_product_command
from app.publishing.domain.events import product_archiving_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: archive_product_command.ArchiveProductCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
) -> None:
    """
    This command handler starts the product archiving process.
    """

    with uow:
        product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value)
        )

        if product_entity.status != product.ProductStatus.Created:
            raise domain_exception.DomainException("Only products with status 'Created' can be archived")

        # Update product status as archiving
        uow.get_repository(product.ProductPrimaryKey, product.Product).update_attributes(
            pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value),
            status=product.ProductStatus.Archiving,
            lastUpdatedBy=cmd.archivedBy.value,
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        uow.commit()

    # Publish the product archiving started message
    message_bus.publish(
        product_archiving_started.ProductArchivingStarted(
            project_id=cmd.projectId.value,
            product_id=cmd.productId.value,
        )
    )
