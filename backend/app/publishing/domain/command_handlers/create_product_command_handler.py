from datetime import datetime, timezone

from app.publishing.domain.commands import create_product_command
from app.publishing.domain.events import product_created
from app.publishing.domain.model import product
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_product_command.CreateProductCommand,
    unit_of_work: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
):
    current_time = datetime.now(timezone.utc).isoformat()

    product_entity = product.Product(
        projectId=command.projectId.value,
        productId=command.productId.value,
        technologyId=command.technologyId.value,
        technologyName=command.technologyName.value,
        productName=command.productName.value,
        productType=command.productType.value,
        productDescription=command.productDescription.value,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.userId.value,
        lastUpdatedBy=command.userId.value,
        status=product.ProductStatus.Created,
    )

    with unit_of_work:
        unit_of_work.get_repository(product.ProductPrimaryKey, product.Product).add(product_entity)
        unit_of_work.commit()

    message_bus.publish(
        product_created.ProductCreated(
            project_id=product_entity.projectId,
            product_name=product_entity.productName,
            product_description=product_entity.productDescription,
            technology_id=product_entity.technologyId,
            user_id=product_entity.createdBy,
            product_id=product_entity.productId,
            product_type=command.productType.value,
        )
    )
