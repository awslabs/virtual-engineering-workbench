import typing
from datetime import datetime, timezone

from app.publishing.domain.commands import create_version_command
from app.publishing.domain.events import product_version_creation_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import (
    amis_query_service,
    iac_service,
    portfolios_query_service,
    template_service,
    versions_query_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.value_objects import product_type_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.api import parameter_service

INITIAL_VERSION = version.format_version_name("1", "0", "0", version.VersionType.ReleaseCandidate, "1")


def _check_versions_limit(
    param_service: parameter_service.ParameterService,
    product_version_limit_param_name: str,
    version_qry_srv: versions_query_service.VersionsQueryService,
    product_entity: product.Product,
    product_rc_version_limit_param_name: str,
):
    # Fetch current version limit
    version_limit = int(param_service.get_parameter_value(parameter_name=product_version_limit_param_name))

    # Fetch current number of versions
    number_of_versions = version_qry_srv.get_distinct_number_of_versions(
        product_id=product_entity.productId,
        status=version.VersionStatus.Created,
    )

    # Check if there are not more versions available than allowed by the limit
    if number_of_versions >= version_limit:
        raise domain_exception.DomainException(
            "You have reached the maximum number of active versions for this product."
        )

    # Fetch current RC version limit
    rc_version_limit = int(param_service.get_parameter_value(parameter_name=product_rc_version_limit_param_name))

    # Fetch current number of RC versions
    number_of_rc_versions = version_qry_srv.get_distinct_number_of_versions(
        product_id=product_entity.productId,
        status=version.VersionStatus.Created,
        version_name_filter=version.VersionType.ReleaseCandidate.suffix,
    )

    # Check if there are not more RC versions available than allowed by the limit
    if number_of_rc_versions >= rc_version_limit:
        raise domain_exception.DomainException(
            "You have reached the maximum number of active RC versions for this product."
        )


def _calculate_new_version_name(
    version_qry_srv: versions_query_service.VersionsQueryService, command: create_version_command.CreateVersionCommand
):
    if command.versionReleaseType.value == version.VersionReleaseType.Major and command.majorVersionName:
        raise domain_exception.DomainException(
            "You cannot create a new major version when selecting an existing major version."
        )
    new_version_name = INITIAL_VERSION
    latest_product_version_name = version_qry_srv.get_latest_version_name_and_id(
        product_id=command.productId.value,
        version_name_begins_with=f"{command.majorVersionName.value}." if command.majorVersionName else None,
    )[0]
    if latest_product_version_name:
        version_name_pieces = latest_product_version_name.split(".")
        major = version_name_pieces[0]
        minor = version_name_pieces[1]
        patch = version_name_pieces[2].split("-")[0] if "-" in version_name_pieces[2] else version_name_pieces[2]

        if command.versionReleaseType.value == version.VersionReleaseType.Major:
            major = str(int(major) + 1)
            minor = "0"
            patch = "0"
        elif command.versionReleaseType.value == version.VersionReleaseType.Minor:
            minor = str(int(minor) + 1)
            patch = "0"
        elif command.versionReleaseType.value == version.VersionReleaseType.Patch:
            patch = str(int(patch) + 1)

        new_version_name = version.format_version_name(major, minor, patch, version.VersionType.ReleaseCandidate, "1")
    return new_version_name


def handle(
    command: create_version_command.CreateVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    portf_qry_srv: portfolios_query_service.PortfoliosQueryService,
    version_qry_srv: versions_query_service.VersionsQueryService,
    param_service: parameter_service.ParameterService,
    product_version_limit_param_name: str,
    product_rc_version_limit_param_name: str,
    stack_srv: iac_service.IACService,
    amis_qry_srv: amis_query_service.AMIsQueryService,
    file_service: template_service.TemplateService,
    template_query_service: template_domain_query_service.TemplateDomainQueryService,
):
    with uow:
        product_entity: product.Product = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
            pk=product.ProductPrimaryKey(projectId=command.projectId.value, productId=command.productId.value)
        )
    if product_entity.status != product.ProductStatus.Created:
        raise domain_exception.DomainException(
            "New product version can be created only from product with status 'Created'"
        )
    fetched_dev_portfolios: typing.List[portfolio.Portfolio] = portf_qry_srv.get_portfolios_by_tech_and_stage(
        product_entity.technologyId, portfolio.PortfolioStage.DEV.value
    )
    if not fetched_dev_portfolios:
        raise domain_exception.DomainException("No portfolio found for DEV stage. Account setup might be incomplete.")

    _check_versions_limit(
        param_service,
        product_version_limit_param_name,
        version_qry_srv,
        product_entity,
        product_rc_version_limit_param_name,
    )

    version_id = version.generate_version_id()

    new_version_name = _calculate_new_version_name(version_qry_srv, command)

    # Validate the template and get parameters
    is_valid, parameters, error_message = stack_srv.validate_template(
        template_body=command.versionTemplateDefinition.value
    )
    if not is_valid:
        raise domain_exception.DomainException(f"The template is invalid: {error_message}")

    # Upload template to S3
    template_file_name = template_query_service.get_default_template_file_name(
        product_type=product_type_value_object.from_str(product_entity.productType.value), is_draft=True
    )
    template_path = f"{command.productId.value}/{version_id}/{template_file_name}"
    file_service.put_template(template_path=template_path, content=command.versionTemplateDefinition.value.encode())

    # Determine additional attribute based on productType
    additional_attributes = {}
    if product_entity.productType == product.ProductType.Container:
        additional_attributes["imageTag"] = command.imageTag.value
        additional_attributes["imageDigest"] = command.imageDigest.value
    else:
        # Get Ami
        ami = amis_qry_srv.get_ami(command.amiId.value)
        if not ami:
            raise domain_exception.DomainException(f"AMI {command.amiId.value} not found")
        additional_attributes["originalAmiId"] = command.amiId.value
        additional_attributes["componentVersionDetails"] = ami.componentVersionDetails
        additional_attributes["osVersion"] = ami.osVersion
        additional_attributes["platform"] = ami.platform
        additional_attributes["architecture"] = ami.architecture
        additional_attributes["integrations"] = ami.integrations or []

    for portf in fetched_dev_portfolios:
        current_time = datetime.now(timezone.utc).isoformat()
        version_entity = version.Version(
            versionId=version_id,
            projectId=command.projectId.value,
            versionName=new_version_name,
            versionType=version.VersionType.ReleaseCandidate.text,
            draftTemplateLocation=template_path,
            scPortfolioId=portf.scPortfolioId,
            productId=command.productId.value,
            versionDescription=command.versionDescription.value,
            technologyId=product_entity.technologyId,
            awsAccountId=portf.awsAccountId,
            accountId=portf.accountId,
            stage=version.VersionStage.DEV,
            region=portf.region,
            status=version.VersionStatus.Creating,
            isRecommendedVersion=False,
            parameters=parameters,
            createDate=current_time,
            lastUpdateDate=current_time,
            createdBy=command.createdBy.value,
            lastUpdatedBy=command.createdBy.value,
            **additional_attributes,
        )

        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).add(version_entity)
            uow.commit()

        message_bus.publish(
            product_version_creation_started.ProductVersionCreationStarted(
                product_id=version_entity.productId,
                version_id=version_entity.versionId,
                aws_account_id=version_entity.awsAccountId,
                product_type=product_entity.productType,
            )
        )
