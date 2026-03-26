from datetime import datetime, timezone

from app.publishing.domain.commands import restore_version_command
from app.publishing.domain.events import product_version_restoration_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import portfolios_query_service, template_service, versions_query_service
from app.publishing.domain.query_services import template_domain_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.api import parameter_service


def _handle_prev_version_distribution_errors(prev_vers_distributions):
    if not prev_vers_distributions:
        raise domain_exception.DomainException("Product version distributions are not found.")
    if any(dist.status != version.VersionStatus.Retired for dist in prev_vers_distributions):
        raise domain_exception.DomainException(
            "Product version can only be restored if the statuses of all distributed versions are 'Retired'."
        )
    if any(dist.versionType != version.VersionType.Released.text for dist in prev_vers_distributions):
        raise domain_exception.DomainException("Only released versions can be restored.")


def handle(
    cmd: restore_version_command.RestoreVersionCommand,
    uow: unit_of_work.UnitOfWork,
    msg_bus: message_bus.MessageBus,
    portfolios_qry_srv: portfolios_query_service.PortfoliosQueryService,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    param_service: parameter_service.ParameterService,
    product_version_limit_param_name: str,
    file_service: template_service.TemplateService,
    template_query_service: template_domain_query_service.TemplateDomainQueryService,
) -> str:
    # Fetch product entity & validate
    with uow:
        product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=cmd.projectId.value, productId=cmd.productId.value)
        )
    if product_entity.status != product.ProductStatus.Created:
        raise domain_exception.DomainException("Product can only be restored if it's status is 'Created'.")

    # Fetch previous version distributions & validate
    prev_vers_distributions = versions_qry_srv.get_product_version_distributions(
        product_id=cmd.productId.value, version_id=cmd.versionId.value
    )
    _handle_prev_version_distribution_errors(prev_vers_distributions)

    # Fetch dev portfolios & validate
    dev_portfolios = portfolios_qry_srv.get_portfolios_by_tech_and_stage(
        product_entity.technologyId, portfolio.PortfolioStage.DEV
    )
    if not dev_portfolios:
        raise domain_exception.DomainException("No portfolio found for stage 'DEV'. Account setup might be incomplete.")

    # Fetch current version limit
    version_limit = int(param_service.get_parameter_value(parameter_name=product_version_limit_param_name))

    # Fetch current number of versions
    number_of_versions = versions_qry_srv.get_distinct_number_of_versions(
        product_id=product_entity.productId,
        status=version.VersionStatus.Created,
    )

    # Check if there are not more versions available than allowed by the limit
    if number_of_versions >= version_limit:
        raise domain_exception.DomainException(
            "You have reached the maximum number of active versions for this product."
        )

    # Calculate the new version name
    # We find the latest restored version of the same version root and increase the counter by 1
    # For example; if we get 1.0.0-restored.1 as the latest restored version name, new version name must be 1.0.0-restored.2
    original_version_entity = prev_vers_distributions[0]
    latest_restored_version_name = versions_qry_srv.get_latest_version_name_and_id(
        product_id=cmd.productId.value,
        version_name_begins_with=version.format_version_name_from_root(
            original_version_entity.versionName, version.VersionType.Restored
        ),
    )[0]
    restored_version_counter = "1"
    if latest_restored_version_name:
        restored_version_counter = str(
            int(latest_restored_version_name.split(version.VersionType.Restored.suffix)[1]) + 1
        )
    restored_version_name = version.format_version_name_from_root(
        original_version_entity.versionName, version.VersionType.Restored, restored_version_counter
    )
    new_version_id = version.generate_version_id()

    # Get template from S3
    downloaded_template_path = file_service.get_template(template_path=original_version_entity.draftTemplateLocation)

    # Upload template to S3
    template_file_name = template_query_service.get_default_template_file_name(
        product_type=product_entity.productType, is_draft=True
    )
    template_path = f"{cmd.productId.value}/{new_version_id}/{template_file_name}"
    with open(downloaded_template_path, "r") as template_file:
        file_service.put_template(template_path=template_path, content=template_file.read())

    # Create version entities and publish events
    with uow:
        for portf in dev_portfolios:
            current_time = datetime.now(timezone.utc).isoformat()
            version_entity = version.Version(
                projectId=cmd.projectId.value,
                productId=cmd.productId.value,
                technologyId=product_entity.technologyId,
                versionId=new_version_id,
                versionName=restored_version_name,
                versionDescription=original_version_entity.versionDescription,
                versionType=version.VersionType.Restored.text,
                draftTemplateLocation=template_path,
                awsAccountId=portf.awsAccountId,
                accountId=portf.accountId,
                stage=version.VersionStage.DEV,
                region=portf.region,
                originalAmiId=original_version_entity.originalAmiId,
                status=version.VersionStatus.Creating,
                scPortfolioId=portf.scPortfolioId,
                isRecommendedVersion=False,
                restoredFromVersionName=original_version_entity.versionName,
                componentVersionDetails=original_version_entity.componentVersionDetails,
                osVersion=original_version_entity.osVersion,
                createDate=current_time,
                lastUpdateDate=current_time,
                createdBy=cmd.restoredBy.value,
                lastUpdatedBy=cmd.restoredBy.value,
            )

            uow.get_repository(version.VersionPrimaryKey, version.Version).add(version_entity)
            uow.commit()

            msg_bus.publish(
                product_version_restoration_started.ProductVersionRestorationStarted(
                    product_id=version_entity.productId,
                    version_id=version_entity.versionId,
                    aws_account_id=version_entity.awsAccountId,
                    old_version_id=original_version_entity.versionId,
                    product_type=product_entity.productType,
                )
            )

    return restored_version_name
