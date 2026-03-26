import logging
from datetime import datetime, timezone

from app.publishing.domain.commands import unpublish_version_command
from app.publishing.domain.events import product_version_unpublished
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import catalog_query_service, catalog_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: unpublish_version_command.UnpublishVersionCommand,
    uow: unit_of_work.UnitOfWork,
    catalog_srv: catalog_service.CatalogService,
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    logger: logging.Logger,
    msg_bus: message_bus.MessageBus,
):
    try:
        with uow:
            version_entity = uow.get_repository(version.VersionPrimaryKey, version.Version).get(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=command.awsAccountId.value,
                ),
            )
            if catalog_qry_srv.does_provisioning_artifact_exist_in_sc(
                region=version_entity.region,
                sc_product_id=version_entity.scProductId,
                sc_provisioning_artifact_id=version_entity.scProvisioningArtifactId,
            ):
                # Check how many provisioning artifacts exist in the same sc product
                # This is required because service catalog does not allow removing the last provisioning artifact
                provisioning_artifact_count = catalog_qry_srv.get_provisioning_artifact_count_in_sc(
                    region=version_entity.region, sc_product_id=version_entity.scProductId
                )

                # Delete the version if there are more than 1 versions available
                if provisioning_artifact_count > 1:
                    catalog_srv.delete_provisioning_artifact(
                        region=version_entity.region,
                        sc_product_id=version_entity.scProductId,
                        sc_provisioning_artifact_id=version_entity.scProvisioningArtifactId,
                    )
                # Delete the entire sc product if this is the last version
                elif provisioning_artifact_count == 1:
                    # Disassociate product from portfolio
                    catalog_srv.disassociate_product_from_portfolio(
                        region=version_entity.region,
                        sc_portfolio_id=version_entity.scPortfolioId,
                        sc_product_id=version_entity.scProductId,
                    )

                    # Delete product in service catalog
                    catalog_srv.delete_product(region=version_entity.region, sc_product_id=version_entity.scProductId)
                # This should never happen
                else:
                    raise domain_exception.DomainException(
                        "Failed to unpublish a version. There is a misconfiguration in Service Catalog."
                    )

            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=command.awsAccountId.value,
                ),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                status=version.VersionStatus.Retired,
            )
            uow.commit()

        # Publish event
        msg_bus.publish(
            product_version_unpublished.ProductVersionUnpublished(
                projectId=version_entity.projectId,
                productId=command.productId.value,
                versionId=command.versionId.value,
                awsAccountId=command.awsAccountId.value,
                region=version_entity.region,
                stage=version_entity.stage.value,
                amiId=version_entity.copiedAmiId,
                integrations=version_entity.integrations,
                hasIntegrations=len(version_entity.integrations or []) > 0,
            )
        )
    except Exception as e:
        logger.exception("Failed to unpublish a version")

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
        raise domain_exception.DomainException("Failed to unpublish a version") from e
