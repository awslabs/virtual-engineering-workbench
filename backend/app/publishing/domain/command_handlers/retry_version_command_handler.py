from datetime import datetime, timezone

from app.publishing.domain.commands import retry_version_command
from app.publishing.domain.events import product_version_retry_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: retry_version_command.RetryVersionCommand,
    uow: unit_of_work.UnitOfWork,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    product_qry_srv: products_query_service.ProductsQueryService,
    message_bus: message_bus.MessageBus,
):
    product_entity = product_qry_srv.get_product(project_id=cmd.projectId.value, product_id=cmd.productId.value)
    if not product_entity:
        raise domain_exception.DomainException("Can not retry product version if product does not exist")

    # Fetch version distributions which will be retried
    fetched_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id=cmd.productId.value,
        version_id=cmd.versionId.value,
        aws_account_ids=[acc.value for acc in cmd.awsAccountIds],
    )
    if not fetched_version_distributions:
        raise domain_exception.DomainException("Product version distributions are not found")

    # Do a validation to check if all version distributions are in failed state
    if any(dist.status != version.VersionStatus.Failed for dist in fetched_version_distributions):
        raise domain_exception.DomainException(
            "Product version distribution can only be retried if it is in Failed state"
        )

    # Update the entities and publish update started event
    with uow:
        for version_distribution in fetched_version_distributions:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=cmd.productId.value,
                    versionId=cmd.versionId.value,
                    awsAccountId=version_distribution.awsAccountId,
                ),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                lastUpdatedBy=cmd.lastUpdatedBy.value,
                status=version.VersionStatus.Updating,
            )
            uow.commit()

            message_bus.publish(
                product_version_retry_started.ProductVersionRetryStarted(
                    product_id=cmd.productId.value,
                    version_id=cmd.versionId.value,
                    aws_account_id=version_distribution.awsAccountId,
                    product_type=product_entity.productType,
                )
            )
