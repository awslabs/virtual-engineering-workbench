import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import create_license_grant_command
from app.publishing.domain.events import license_grant_created
from app.publishing.domain.model import license_grant
from app.publishing.domain.model.marketplace_metadata import MarketplaceMetadata
from app.publishing.domain.ports import amis_query_service, license_manager_service
from app.publishing.domain.read_models.create_license_grant_result import CreateLicenseGrantResult
from app.publishing.domain.value_objects import grant_id_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_license_grant_command.CreateLicenseGrantCommand,
    uow: unit_of_work.UnitOfWork,
    license_manager_service: license_manager_service.LicenseManagerService,
    msg_bus: message_bus.MessageBus,
    amis_query_service: amis_query_service.AMIsQueryService,
    logger: logging.Logger,
) -> CreateLicenseGrantResult:
    ami_entity = amis_query_service.get_ami(command.amiId.value)
    image_marketplace_metadata = (
        ami_entity.marketplaceMetadata if ami_entity and ami_entity.marketplaceMetadata else MarketplaceMetadata()
    )

    license_arn, home_region = image_marketplace_metadata.parse_grant_arn_components()

    principal_arn = f"arn:aws:iam::{command.targetAccountId.value}:root"
    result = license_manager_service.create_grant(
        license_arn=license_arn,
        principal_arn=principal_arn,
        grant_name=command.grantName.value,
        home_region=home_region,
    )

    grant_id = grant_id_value_object.generate().value
    current_time = datetime.now(timezone.utc).isoformat()
    grant_entity = license_grant.LicenseGrant(
        grantId=grant_id,
        projectId=command.projectId.value,
        imageId=command.amiId.value,
        licenseArn=license_arn,
        grantArn=result.grantArn,
        homeRegion=home_region,
        targetAccountId=command.targetAccountId.value,
        status=license_grant.LicenseGrantStatus.PendingAcceptance,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(license_grant.LicenseGrantPrimaryKey, license_grant.LicenseGrant).add(grant_entity)
        uow.commit()

    msg_bus.publish(
        license_grant_created.LicenseGrantCreated(
            projectId=command.projectId.value,
            imageId=command.amiId.value,
            grantId=grant_id,
            grantArn=result.grantArn,
            targetAccountId=command.targetAccountId.value,
            licenseArn=license_arn,
        )
    )

    logger.debug("License grant created: %s", grant_id)
    return CreateLicenseGrantResult(grantId=grant_id, grantArn=result.grantArn, homeRegion=home_region)
