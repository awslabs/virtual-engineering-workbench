import logging

from app.publishing.domain.read_models import ami
from app.publishing.domain.value_objects import ami_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    ami_id: ami_id_value_object.AmiIdValueObject,
    uow: unit_of_work.UnitOfWork,
    logger: logging.Logger,
) -> None:
    with uow:
        ami_repo = uow.get_repository(ami.AmiPrimaryKey, ami.Ami)
        ami_repo.remove(pk=ami.AmiPrimaryKey(amiId=ami_id.value))
        uow.commit()
        logger.debug(f"Removed ami {ami_id.value} from db.")
