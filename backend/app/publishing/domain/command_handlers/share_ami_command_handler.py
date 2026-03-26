import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import share_ami_command
from app.publishing.domain.model import shared_ami
from app.publishing.domain.ports import image_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: share_ami_command.ShareAmiCommand,
    uow: unit_of_work.UnitOfWork,
    img_srv: image_service.ImageService,
    logger: logging.Logger,
) -> None:
    """
    This command handler shares ami with use case account and stores the shared ami
    """

    # Grant KMS access to the spoke account for the AMI's encrypted snapshots
    img_srv.grant_kms_access(
        region=cmd.region.value, ami_id=cmd.copiedAmiId.value, aws_account_id=cmd.awsAccountId.value
    )
    logger.debug("KMS access granted.")

    # Share the AMI to the target account
    img_srv.share_ami(
        region=cmd.region.value, copied_ami_id=cmd.copiedAmiId.value, aws_account_id=cmd.awsAccountId.value
    )
    logger.debug("AMI sharing finished.")

    # Store the shared Ami entity to database
    current_time = datetime.now(timezone.utc).isoformat()
    shared_ami_entity = shared_ami.SharedAmi(
        originalAmiId=cmd.originalAmiId.value,
        copiedAmiId=cmd.copiedAmiId.value,
        awsAccountId=cmd.awsAccountId.value,
        region=cmd.region.value,
        createDate=current_time,
        lastUpdateDate=current_time,
    )
    with uow:
        uow.get_repository(shared_ami.SharedAmiPrimaryKey, shared_ami.SharedAmi).add(shared_ami_entity)
        uow.commit()
