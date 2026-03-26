import logging

from app.publishing.domain.read_models import ami
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    new_ami: ami.Ami,
    retired_ami_ids: list[str],
    uow: unit_of_work.UnitOfWork,
    logger: logging.Logger,
) -> None:
    with uow:
        ami_repo = uow.get_repository(ami.AmiPrimaryKey, ami.Ami)

        # Delete retired amis
        if retired_ami_ids:
            __delete_retired_amis(retired_ami_ids, uow, ami_repo, logger)

        # Insert new ami to db
        ami_repo.add(new_ami)
        uow.commit()
        logger.debug(f"Added ami {new_ami.amiId} to db.")


def __delete_retired_amis(
    retired_ami_ids: list[str],
    uow: unit_of_work.UnitOfWork,
    ami_repo: unit_of_work.GenericRepository,
    logger: logging.Logger,
) -> None:
    commit_counter = 0
    for retired_ami_id in retired_ami_ids:
        retired_ami = ami_repo.get(pk=ami.AmiPrimaryKey(amiId=retired_ami_id))
        if not retired_ami:
            continue

        ami_repo.remove(pk=ami.AmiPrimaryKey(amiId=retired_ami_id))

        commit_counter += 1
        logger.debug(f"Deleted ami {retired_ami_id} from db.")
        if commit_counter % 10 == 0:  # Commit in batches of 10
            uow.commit()
            commit_counter = 0
    if commit_counter:  # Commit in the end if there was any new ami
        uow.commit()
