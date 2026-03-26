import logging
from datetime import datetime, timezone

import jinja2

from app.publishing.domain.commands import publish_version_command
from app.publishing.domain.events import (
    product_version_published,
    product_version_update_started,
)
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import (
    catalog_query_service,
    catalog_service,
    projects_query_service,
    shared_amis_query_service,
    template_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def _delete_previous_rc_version(
    cmd: publish_version_command.PublishVersionCommand,
    vers: version.Version,
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    catalog_srv: catalog_service.CatalogService,
    sc_product_id: str | None,
):
    if (
        cmd.previousEventName.value == product_version_update_started.ProductVersionUpdateStarted.__name__
        and vers.versionType == version.VersionType.ReleaseCandidate.text
        and not vers.versionName.endswith(version.VersionType.ReleaseCandidate.suffix_format.format("1"))
    ):
        # Calculate the previous version name by decreasing rc counter by 1
        prev_rc_counter = str(int(vers.versionName.split(".")[-1]) - 1)
        prev_version_name = vers.versionName[: vers.versionName.rfind(".")] + "." + prev_rc_counter

        # Check if previous version was created in catalog
        old_sc_provisioning_artifact_id = catalog_qry_srv.get_sc_provisioning_artifact_id(
            region=vers.region,
            sc_product_id=vers.scProductId,
            sc_version_name=prev_version_name,
        )

        # Delete the previous version if created
        if old_sc_provisioning_artifact_id:
            catalog_srv.delete_provisioning_artifact(
                region=vers.region,
                sc_product_id=sc_product_id,
                sc_provisioning_artifact_id=old_sc_provisioning_artifact_id,
            )


def handle(
    cmd: publish_version_command.PublishVersionCommand,
    uow: unit_of_work.UnitOfWork,
    catalog_qry_srv: catalog_query_service.CatalogQueryService,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    catalog_srv: catalog_service.CatalogService,
    logger: logging.Logger,
    msg_bus: message_bus.MessageBus,
    file_srv: template_service.TemplateService,
    shared_amis_qry_srv: shared_amis_query_service.SharedAMIsQueryService,
    template_qry_srv: template_domain_query_service.TemplateDomainQueryService,
) -> None:
    """
    This command handler publishes product version to aws account and stage.
    """
    try:
        vers, prod = _get_version_and_product(cmd, uow)
        proj = projects_qry_srv.get_project(vers.projectId)
        template_path = _upload_template(
            vers=vers,
            prod=prod,
            file_srv=file_srv,
            shared_amis_qry_srv=shared_amis_qry_srv,
            template_qry_srv=template_qry_srv,
        )

        sc_product_id, sc_provisioning_artifact_id = _ensure_product_and_version(
            catalog_qry_srv, catalog_srv, vers, prod, template_path
        )

        # Associate product with portfolio
        catalog_srv.associate_product_with_portfolio(
            region=vers.region,
            sc_portfolio_id=vers.scPortfolioId,
            sc_product_id=sc_product_id,
        )

        # Check if launch constraint is created before
        launch_constraint_id = catalog_qry_srv.get_launch_constraint_id(
            region=vers.region,
            sc_portfolio_id=vers.scPortfolioId,
            sc_product_id=sc_product_id,
        )

        # Create launch constraint if not created before
        if not launch_constraint_id:
            catalog_srv.create_launch_constraint(
                region=vers.region,
                sc_portfolio_id=vers.scPortfolioId,
                sc_product_id=sc_product_id,
            )

        # Check if notification constraint is created before
        notification_constraint_id = catalog_qry_srv.get_notification_constraint_id(
            region=vers.region,
            sc_portfolio_id=vers.scPortfolioId,
            sc_product_id=sc_product_id,
        )

        # Create notification constraint if it does not exist
        if not notification_constraint_id:
            catalog_srv.create_notification_constraint(
                region=vers.region,
                sc_portfolio_id=vers.scPortfolioId,
                sc_product_id=sc_product_id,
            )

        # Check if resource update constraint is created before
        resource_update_constraint_id = catalog_qry_srv.get_resource_update_constraint_id(
            region=vers.region,
            sc_portfolio_id=vers.scPortfolioId,
            sc_product_id=sc_product_id,
        )

        # Create resource update constraint if it does not exist
        if not resource_update_constraint_id:
            catalog_srv.create_resource_update_constraint(
                region=vers.region,
                sc_portfolio_id=vers.scPortfolioId,
                sc_product_id=sc_product_id,
            )

        # Get provisioning parameters to store them in version entity
        parameters, version_metadata = catalog_qry_srv.get_provisioning_parameters(
            region=vers.region,
            sc_product_id=sc_product_id,
            sc_provisioning_artifact_id=sc_provisioning_artifact_id,
        )

        _delete_previous_rc_version(cmd, vers, catalog_qry_srv, catalog_srv, sc_product_id)

        # Update data and set status to successful
        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=cmd.productId.value,
                    versionId=cmd.versionId.value,
                    awsAccountId=cmd.awsAccountId.value,
                ),
                scProductId=sc_product_id,
                scProvisioningArtifactId=sc_provisioning_artifact_id,
                templateLocation=template_path,
                status=version.VersionStatus.Created,
                parameters=[param.dict() for param in parameters],
                metadata=({key: val.dict() for key, val in version_metadata.items()} if version_metadata else None),
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

        # Publish event
        additional_attributes = {}
        additional_attributes["amiId"] = vers.copiedAmiId
        additional_attributes["platform"] = vers.platform
        additional_attributes["architecture"] = vers.architecture
        additional_attributes["integrations"] = vers.integrations or []
        additional_attributes["hasIntegrations"] = len(vers.integrations or []) > 0
        msg_bus.publish(
            product_version_published.ProductVersionPublished(
                projectId=proj.projectId,
                projectName=proj.projectName,
                productId=cmd.productId.value,
                productName=prod.productName,
                versionId=cmd.versionId.value,
                awsAccountId=cmd.awsAccountId.value,
                stage=vers.stage,
                region=vers.region,
                version_name=vers.versionName,
                version_description=vers.versionDescription,
                sc_product_id=sc_product_id,
                sc_provisioning_artifact_id=sc_provisioning_artifact_id,
                **additional_attributes,
            )
        )

    except Exception as e:
        logger.exception("Failed to publish version")

        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=cmd.productId.value,
                    versionId=cmd.versionId.value,
                    awsAccountId=cmd.awsAccountId.value,
                ),
                status=version.VersionStatus.Failed,
                lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            )
            uow.commit()

        raise domain_exception.DomainException("Failed to publish version") from e


def _get_version_and_product(cmd, uow):
    with uow:
        vers = uow.get_repository(version.VersionPrimaryKey, version.Version).get(
            pk=version.VersionPrimaryKey(
                productId=cmd.productId.value,
                versionId=cmd.versionId.value,
                awsAccountId=cmd.awsAccountId.value,
            )
        )
        prod = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=vers.projectId, productId=vers.productId)
        )
    return vers, prod


def _ensure_product_and_version(catalog_qry_srv, catalog_srv, vers, prod, template_path):
    sc_product_name = f"{prod.productId}-{vers.awsAccountId}"
    sc_product_id = catalog_qry_srv.get_sc_product_id(region=vers.region, sc_product_name=sc_product_name)
    if sc_product_id:
        sc_provisioning_artifact_id = catalog_qry_srv.get_sc_provisioning_artifact_id(
            region=vers.region,
            sc_product_id=sc_product_id,
            sc_version_name=vers.versionName,
        )
        if not sc_provisioning_artifact_id:
            sc_provisioning_artifact_id = catalog_srv.create_provisioning_artifact(
                region=vers.region,
                version_id=vers.versionId,
                version_name=vers.versionName,
                sc_product_id=sc_product_id,
                description=vers.versionDescription,
                template_path=template_path,
            )
    else:
        sc_product_id, sc_provisioning_artifact_id = catalog_srv.create_product(
            region=vers.region,
            product_name=sc_product_name,
            owner=vers.createdBy,
            product_description=prod.productDescription,
            version_id=vers.versionId,
            version_name=vers.versionName,
            version_description=vers.versionDescription,
            template_path=template_path,
        )
    return sc_product_id, sc_provisioning_artifact_id


def _upload_template(
    vers: version.Version,
    prod: product.Product,
    file_srv: template_service.TemplateService,
    shared_amis_qry_srv: shared_amis_query_service.SharedAMIsQueryService,
    template_qry_srv: template_domain_query_service.TemplateDomainQueryService,
) -> str:
    # Download the draft template
    local_template_path = file_srv.get_template(template_path=vers.draftTemplateLocation)
    if not local_template_path:
        raise domain_exception.DomainException(f"Could not find draft template for {vers.versionId}.")

    # Read the draft template
    with open(local_template_path, "rb") as f:
        cf_template = f.read()

    cf_template = _handle_ami_product(cf_template, shared_amis_qry_srv, vers, prod).encode()
    # Upload template to object storage
    template_file_name = template_qry_srv.get_default_template_file_name(product_type=prod.productType)
    template_path = f"{vers.productId}/{vers.versionId}/{template_file_name}"
    file_srv.put_template(template_path=template_path, content=cf_template)

    return template_path


def _handle_ami_product(
    template: bytes,
    shared_amis_qry_srv: shared_amis_query_service.SharedAMIsQueryService,
    vers: version.Version,
    prod: product.Product,
) -> str:
    # Get all shared amis for the given original ami id
    shared_amis = shared_amis_qry_srv.get_shared_amis(original_ami_id=vers.originalAmiId)
    if not shared_amis:
        raise domain_exception.DomainException(
            f"Could not find any shared ami for {vers.originalAmiId}. Ami sharing process might have failed."
        )
    ami_ids_per_region = {ami.region: ami.copiedAmiId for ami in shared_amis}

    # Replace fields using the Jinja template
    jinja_template = jinja2.Template(template.decode())

    rendered_text = jinja_template.render(
        product_name=prod.productName,
        product_version=vers.versionName,
        ami_ids=ami_ids_per_region,
    )
    return rendered_text
