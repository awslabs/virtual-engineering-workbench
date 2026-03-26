import typing
from datetime import datetime, timezone

from app.publishing.domain.commands import promote_version_command
from app.publishing.domain.events import (
    product_version_name_updated,
    product_version_promotion_started,
)
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import (
    amis_query_service,
    portfolios_query_service,
    versions_query_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def _check_if_instance_type_image_available(
    version_entity: version.Version, amis_qry_srv: amis_query_service.AMIsQueryService
):
    if not version_entity.originalAmiId:
        raise domain_exception.DomainException("Product version does not have original AMI.")
    original_image = amis_qry_srv.get_ami(ami_id=version_entity.originalAmiId)
    if not original_image:
        raise domain_exception.DomainException("Original AMI was retired. Update product version with available AMI")


def _check_if_image_available(
    product_entity: product.Product,
    amis_qry_srv: amis_query_service.AMIsQueryService,
    version_entity: version.Version,
):
    match product_entity.productType:
        case p if p in product.PRODUCT_INSTANCE_TYPES:
            _check_if_instance_type_image_available(version_entity=version_entity, amis_qry_srv=amis_qry_srv)
        case _:
            raise domain_exception.DomainException("Unsupported product type")


def _handle_errors(
    product_entity: product.Product,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    amis_qry_srv: amis_query_service.AMIsQueryService,
    command: promote_version_command.PromoteVersionCommand,
):
    if product_entity.status != product.ProductStatus.Created:
        raise domain_exception.DomainException("Product can only be promoted with status 'Created'")
    fetched_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id=command.productId.value, version_id=command.versionId.value
    )

    if not fetched_version_distributions:
        raise domain_exception.DomainException("Product version not found")

    if any(dist.status != version.VersionStatus.Created for dist in fetched_version_distributions):
        raise domain_exception.DomainException(
            "Product version can only be promoted if the status of all distributed versions is 'Created'"
        )

    if any(dist.stage.value == command.stage.value for dist in fetched_version_distributions):
        raise domain_exception.DomainException("Product version is already distributed to the targeted stage.")

    version_entity = next((vers for vers in fetched_version_distributions), None)

    _check_if_image_available(
        product_entity=product_entity,
        version_entity=version_entity,
        amis_qry_srv=amis_qry_srv,
    )


def handle(
    command: promote_version_command.PromoteVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    portf_qry_srv: portfolios_query_service.PortfoliosQueryService,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    amis_qry_srv: amis_query_service.AMIsQueryService,
):
    with uow:
        product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=command.projectId.value, productId=command.productId.value)
        )

    fetched_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id=command.productId.value, version_id=command.versionId.value
    )

    _handle_errors(
        product_entity=product_entity,
        versions_qry_srv=versions_qry_srv,
        command=command,
        amis_qry_srv=amis_qry_srv,
    )

    original_version_entity = fetched_version_distributions[0]
    version_name = original_version_entity.versionName
    version_type = original_version_entity.versionType

    fetched_portfolios: typing.List[portfolio.Portfolio] = portf_qry_srv.get_portfolios_by_tech_and_stage(
        product_entity.technologyId, command.stage.value
    )
    if not fetched_portfolios:
        raise domain_exception.DomainException(
            "No portfolio found for target stage. Account setup might be incomplete."
        )

    acceptable_roles_for_prod_promotion = [
        VirtualWorkbenchRoles.Admin,
        VirtualWorkbenchRoles.ProgramOwner,
        VirtualWorkbenchRoles.PowerUser,
    ]
    if command.stage.value == portfolio.PortfolioStage.PROD:
        if not any([item.value in acceptable_roles_for_prod_promotion for item in command.userRoles]):
            raise domain_exception.DomainException("User does not have the required role to promote a version to PROD")
        if any(dist.versionType != version.VersionType.ReleaseCandidate.text for dist in fetched_version_distributions):
            raise domain_exception.DomainException("Only release candidate versions can be promoted to PROD")
        version_name = version_name.split(version.VersionType.ReleaseCandidate.suffix)[0]
        version_type = version.VersionType.Released.text
        with uow:
            for version_distribution in fetched_version_distributions:
                current_time = datetime.now(timezone.utc).isoformat()
                uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                    pk=version.VersionPrimaryKey(
                        productId=command.productId.value,
                        versionId=command.versionId.value,
                        awsAccountId=version_distribution.awsAccountId,
                    ),
                    versionName=version_name,
                    versionType=version_type,
                    lastUpdateDate=current_time,
                    lastUpdatedBy=command.createdBy.value,
                    status=version.VersionStatus.Updating,
                )
                uow.commit()

                message_bus.publish(
                    product_version_name_updated.ProductVersionNameUpdated(
                        project_id=command.projectId.value,
                        product_id=version_distribution.productId,
                        version_id=version_distribution.versionId,
                        version_name=version_name,
                        aws_account_id=version_distribution.awsAccountId,
                        has_integrations=len(version_distribution.integrations or []) > 0,
                        integrations=version_distribution.integrations,
                    )
                )
    with uow:
        for portf in fetched_portfolios:
            current_time = datetime.now(timezone.utc).isoformat()
            version_entity = version.Version(
                versionId=command.versionId.value,
                projectId=command.projectId.value,
                versionName=version_name,
                versionType=version_type,
                draftTemplateLocation=original_version_entity.draftTemplateLocation,
                scPortfolioId=portf.scPortfolioId,
                productId=command.productId.value,
                versionDescription=original_version_entity.versionDescription,
                technologyId=product_entity.technologyId,
                awsAccountId=portf.awsAccountId,
                accountId=portf.accountId,
                stage=command.stage.value,
                region=portf.region,
                originalAmiId=original_version_entity.originalAmiId,
                imageTag=original_version_entity.imageTag,
                imageDigest=original_version_entity.imageDigest,
                status=version.VersionStatus.Creating,
                isRecommendedVersion=original_version_entity.isRecommendedVersion,
                restoredFromVersionName=original_version_entity.restoredFromVersionName,
                componentVersionDetails=original_version_entity.componentVersionDetails,
                osVersion=original_version_entity.osVersion,
                integrations=original_version_entity.integrations,
                createDate=current_time,
                lastUpdateDate=current_time,
                createdBy=command.createdBy.value,
                lastUpdatedBy=command.createdBy.value,
            )

            uow.get_repository(version.VersionPrimaryKey, version.Version).add(version_entity)
            uow.commit()

            message_bus.publish(
                product_version_promotion_started.ProductVersionPromotionStarted(
                    product_id=version_entity.productId,
                    version_id=version_entity.versionId,
                    aws_account_id=version_entity.awsAccountId,
                    product_type=product_entity.productType,
                )
            )
