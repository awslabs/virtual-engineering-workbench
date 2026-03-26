import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import rename_version_distributions_command
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import catalog_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: rename_version_distributions_command.RenameVersionDistributionsCommand,
    uow: unit_of_work.UnitOfWork,
    catalog_srv: catalog_service.CatalogService,
    logger: logging.Logger,
):
    try:
        with uow:
            version_entity = uow.get_repository(version.VersionPrimaryKey, version.Version).get(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=command.awsAccountId.value,
                )
            )

            result = catalog_srv.update_provisioning_artifact_name(
                region=version_entity.region,
                sc_product_id=version_entity.scProductId,
                sc_provisioning_artifact_id=version_entity.scProvisioningArtifactId,
                new_name=version_entity.versionName,
            )

            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=command.awsAccountId.value,
                ),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                status=version.VersionStatus.Failed if result == "FAILED" else version.VersionStatus.Created,
            )
            uow.commit()
    except Exception as e:
        logger.exception("Failed to rename the version.")

        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=command.awsAccountId.value,
                ),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                status=version.VersionStatus.Failed,
            )
            uow.commit()
        raise domain_exception.DomainException("Failed to rename the version.") from e
