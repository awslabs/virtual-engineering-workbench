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
    license_manager_service.accept_grant(
        grant_arn=command.grantArn.value,
        home_region=command.homeRegion.value,
        spoke_account_id=command.targetAccountId.value,
    )

    current_time = datetime.now(timezone.utc).isoformat()
    with uow:
        grant_entity = uow.get_repository(license_grant.LicenseGrantPrimaryKey, license_grant.LicenseGrant).get(
            license_grant.LicenseGrantPrimaryKey(projectId=command.projectId.value, grantId=command.grantId.value)
        )
        if not grant_entity:
            raise domain_exception.DomainException("License grant %s not found." % command.grantId.value)
        grant_entity.status = license_grant.LicenseGrantStatus.Active
        grant_entity.lastUpdateDate = current_time
        uow.get_repository(license_grant.LicenseGrantPrimaryKey, license_grant.LicenseGrant).update_entity(
            license_grant.LicenseGrantPrimaryKey(projectId=command.projectId.value, grantId=command.grantId.value),
            grant_entity,
        )
        uow.commit()

    msg_bus.publish(
        license_grant_accepted.LicenseGrantAccepted(
            grantId=command.grantId.value,
            grantArn=command.grantArn.value,
            targetAccountId=grant_entity.targetAccountId,
        )
    )

    logger.debug("License grant accepted: %s", command.grantId.value)
