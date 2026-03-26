import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import fail_ami_sharing_command
from app.publishing.domain.model import version
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: fail_ami_sharing_command.FailAmiSharingCommand,
    uow: unit_of_work.UnitOfWork,
    logger: logging.Logger,
) -> None:
    """
    This command handler updates the product version with failed status
    """

    # Update product version entity as failed
    with uow:
        uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
            pk=version.VersionPrimaryKey(
                productId=cmd.productId.value, versionId=cmd.versionId.value, awsAccountId=cmd.awsAccountId.value
            ),
            status=version.VersionStatus.Failed,
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        uow.commit()

    logger.error(
        f"Ami sharing failed. Product Id: {cmd.productId.value}, Version Id: {cmd.versionId.value}, AWS Account Id: {cmd.awsAccountId.value}"
    )
