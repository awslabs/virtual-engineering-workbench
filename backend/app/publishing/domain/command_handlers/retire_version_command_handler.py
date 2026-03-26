from datetime import datetime, timezone

from app.publishing.domain.commands import retire_version_command
from app.publishing.domain.events import product_version_retirement_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import versions_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def handle(  # noqa: C901
    command: retire_version_command.RetireVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    versions_qry_srv: versions_query_service.VersionsQueryService,
):
    with uow:
        product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=command.projectId.value, productId=command.productId.value)
        )
    if product_entity.status != product.ProductStatus.Created:
        raise domain_exception.DomainException("Product can only be retired with status 'Created'")
    fetched_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id=command.productId.value, version_id=command.versionId.value
    )

    if not fetched_version_distributions:
        raise domain_exception.DomainException("Product version not found")

    if any(dist.status != version.VersionStatus.Created for dist in fetched_version_distributions):
        raise domain_exception.DomainException(
            "Product version can only be retired if the status of all distributed versions is 'Created'"
        )
    latest_version_name = versions_qry_srv.get_latest_version_name_and_id(product_id=command.productId.value)[0]
    if latest_version_name == fetched_version_distributions[0].versionName:
        raise domain_exception.DomainException("Latest version can not be retired")

    if any(dist.stage == version.VersionStage.PROD for dist in fetched_version_distributions):
        acceptable_roles_for_version_retire = [
            VirtualWorkbenchRoles.Admin,
            VirtualWorkbenchRoles.ProgramOwner,
            VirtualWorkbenchRoles.PowerUser,
        ]
        if not any([item.value in acceptable_roles_for_version_retire for item in command.userRoles]):
            raise domain_exception.DomainException("Only power users and above can retire a version in PROD stage.")

    with uow:
        if command.versionId.value == product_entity.recommendedVersionId:
            uow.get_repository(product.ProductPrimaryKey, product.Product).update_attributes(
                pk=product.ProductPrimaryKey(projectId=command.projectId.value, productId=command.productId.value),
                recommendedVersionId=None,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                lastUpdatedBy=command.retiredBy.value,
            )

        for version_distribution in fetched_version_distributions:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=version_distribution.awsAccountId,
                ),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
                lastUpdatedBy=command.retiredBy.value,
                status=version.VersionStatus.Retiring,
                retireReason=command.retireReason,
                isRecommendedVersion=False,
            )
            uow.commit()
            message_bus.publish(
                product_version_retirement_started.ProductVersionRetirementStarted(
                    product_id=version_distribution.productId,
                    version_id=version_distribution.versionId,
                    aws_account_id=version_distribution.awsAccountId,
                )
            )
