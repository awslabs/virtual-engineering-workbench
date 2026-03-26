import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import succeed_ami_sharing_command
from app.publishing.domain.events import product_version_ami_shared
from app.publishing.domain.model import product, version
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: succeed_ami_sharing_command.SucceedAmiSharingCommand,
    uow: unit_of_work.UnitOfWork,
    msg_bus: message_bus.MessageBus,
    logger: logging.Logger,
) -> None:
    """
    This command handler updates the product version with the copied ami id and publishes event for ami sharing
    """

    # Update product version entity with copiedAmiId
    if cmd.productType.value != product.ProductType.Container:
        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=cmd.productId.value, versionId=cmd.versionId.value, awsAccountId=cmd.awsAccountId.value
                ),
                copiedAmiId=cmd.copiedAmiId.value,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

    # Publish the ami sharing success message
    msg_bus.publish(
        product_version_ami_shared.ProductVersionAmiShared(
            product_id=cmd.productId.value,
            version_id=cmd.versionId.value,
            aws_account_id=cmd.awsAccountId.value,
            previousEventName=cmd.previousEventName.value,
            oldVersionId=cmd.oldVersionId,
        )
    )

    logger.debug("Ami sharing succeeded")
