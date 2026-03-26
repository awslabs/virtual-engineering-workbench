import logging

from app.publishing.domain.commands import copy_ami_command
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.ports import image_service
from app.publishing.domain.read_models import ami
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: copy_ami_command.CopyAmiCommand,
    uow: unit_of_work.UnitOfWork,
    img_srv: image_service.ImageService,
    logger: logging.Logger,
) -> str:
    """
    This command handler copies ami to another region
    """
    # Get the AMI entity to be copied
    with uow:
        ami_entity: ami.Ami = uow.get_repository(ami.AmiPrimaryKey, ami.Ami).get(
            ami.AmiPrimaryKey(amiId=cmd.originalAmiId.value)
        )

    if not ami_entity:
        raise domain_exception.DomainException(f"The given AMI {cmd.originalAmiId.value} could not be found.")

    # Copy the AMI to the target region
    copied_ami_id = img_srv.copy_ami(
        region=cmd.region.value,
        original_ami_id=cmd.originalAmiId.value,
        ami_name=ami_entity.amiName,
        ami_description=ami_entity.amiDescription,
    )
    logger.debug(f"AMI copying started. Copied Ami Id: {copied_ami_id}")

    # Return the copied ami id
    return copied_ami_id
