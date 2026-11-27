import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import accept_license_grant_command
from app.publishing.domain.events import license_grant_accepted
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import license_grant
from app.publishing.domain.ports import license_manager_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: accept_license_grant_command.AcceptLicenseGrantCommand,
    uow: unit_of_work.UnitOfWork,
    license_manager_service: license_manager_service.LicenseManagerService,
    msg_bus: message_bus.MessageBus,
    logger: logging.Logger,
) -> None:
    current_time = datetime.now(timezone.utc).isoformat()
    # Read the grant record first. Accepting before the lookup meant a command
    # naming a grant this project does not have still issued a real AcceptGrant
    # against the spoke account, and only then failed.
    with uow:
        grant_entity = uow.get_repository(license_grant.LicenseGrantPrimaryKey, license_grant.LicenseGrant).get(
            license_grant.LicenseGrantPrimaryKey(projectId=command.projectId.value, grantId=command.grantId.value)
        )
        if not grant_entity:
            raise domain_exception.DomainException("License grant %s not found." % command.grantId.value)

    license_manager_service.accept_grant(
        grant_arn=grant_entity.grantArn,
        home_region=grant_entity.homeRegion,
        spoke_account_id=grant_entity.targetAccountId,
    )

    # Write only the two fields this command changes. Writing back the whole
    # entity read before the AWS call would overwrite anything another writer
    # changed in the meantime.
    with uow:
        uow.get_repository(license_grant.LicenseGrantPrimaryKey, license_grant.LicenseGrant).update_attributes(
            license_grant.LicenseGrantPrimaryKey(projectId=command.projectId.value, grantId=command.grantId.value),
            status=license_grant.LicenseGrantStatus.Active,
            lastUpdateDate=current_time,
        )
        uow.commit()

    msg_bus.publish(
        license_grant_accepted.LicenseGrantAccepted(
            grantId=grant_entity.grantId,
            grantArn=grant_entity.grantArn,
            targetAccountId=grant_entity.targetAccountId,
        )
    )

    logger.debug("License grant accepted: %s", grant_entity.grantId)
