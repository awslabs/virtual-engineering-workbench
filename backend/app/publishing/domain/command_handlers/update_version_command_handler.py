from datetime import datetime, timezone

from app.publishing.domain.commands import update_version_command
from app.publishing.domain.events import product_version_update_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import amis_query_service, iac_service, template_service, versions_query_service
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import component_version_detail
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: update_version_command.UpdateVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    version_qry_srv: versions_query_service.VersionsQueryService,
    stack_srv: iac_service.IACService,
    amis_qry_srv: amis_query_service.AMIsQueryService,
    file_service: template_service.TemplateService,
    template_query_service: template_domain_query_service.TemplateDomainQueryService,
):
    with uow:
        product_entity: product.Product = __get_product(uow, command)

    __validate_product_for_update(product_entity)

    fetched_version_distributions = __fetch_version_distributions(version_qry_srv, command)

    __validate_version_distributions(fetched_version_distributions)

    # Validate template and calculate new version name
    new_version_name, parameters = __validate_and_generate_version(command, stack_srv, fetched_version_distributions)

    # Upload template
    template_path = __upload_template(command, file_service, template_query_service, product_entity)

    # Determine additional attributes
    additional_attributes = __prepare_additional_attributes(command, product_entity, amis_qry_srv)

    # Update version and publish event
    __update_version(
        uow, new_version_name, fetched_version_distributions, command, additional_attributes, template_path, parameters
    )
    __publish_version_update_started(message_bus, fetched_version_distributions, command, product_entity)


def __get_product(uow, command):
    return uow.get_repository(product.ProductPrimaryKey, product.Product).get(
        pk=product.ProductPrimaryKey(
            projectId=command.projectId.value,
            productId=command.productId.value,
        )
    )


def __validate_product_for_update(product_entity):
    if product_entity.status != product.ProductStatus.Created:
        raise domain_exception.DomainException("Product version can only be updated from product with status 'Created'")


def __fetch_version_distributions(version_qry_srv, command):
    return version_qry_srv.get_product_version_distributions(
        product_id=command.productId.value, version_id=command.versionId.value
    )


def __validate_version_distributions(fetched_version_distributions):
    if len(fetched_version_distributions) == 0:
        raise domain_exception.DomainException("Product version not found")
    if any(dist.stage == version.VersionStage.PROD for dist in fetched_version_distributions):
        raise domain_exception.DomainException(
            "Product version can only be updated if not promoted to production stage"
        )
    if any(dist.versionType != version.VersionType.ReleaseCandidate.text for dist in fetched_version_distributions):
        raise domain_exception.DomainException("Only release candidate versions can be updated")


def __validate_and_generate_version(command, stack_srv, fetched_version_distributions):
    is_valid, parameters, error_message = stack_srv.validate_template(
        template_body=command.versionTemplateDefinition.value
    )
    if not is_valid:
        raise domain_exception.DomainException(f"The template is invalid: {error_message}")

    version_name = fetched_version_distributions[0].versionName
    version_name_root, release_candidate_counter = version_name.split(version.VersionType.ReleaseCandidate.suffix)
    return (
        version.format_version_name_from_root(
            version_name_root, version.VersionType.ReleaseCandidate, str(int(release_candidate_counter) + 1)
        ),
        parameters,
    )


def __upload_template(command, file_service, template_query_service, product_entity):
    template_file_name = template_query_service.get_default_template_file_name(
        product_type=product_entity.productType, is_draft=True
    )
    template_path = f"{command.productId.value}/{command.versionId.value}/{template_file_name}"
    file_service.put_template(template_path=template_path, content=command.versionTemplateDefinition.value.encode())
    return template_path


def __prepare_additional_attributes(command, product_entity, amis_qry_srv):
    additional_attributes = {}
    if product_entity.productType == product.ProductType.Container:
        additional_attributes["imageTag"] = command.imageTag.value
        additional_attributes["imageDigest"] = command.imageDigest.value
    else:
        ami = amis_qry_srv.get_ami(command.amiId.value)
        if not ami:
            raise domain_exception.DomainException(f"AMI {command.amiId.value} not found")
        additional_attributes["originalAmiId"] = command.amiId.value
        additional_attributes["componentVersionDetails"] = (
            [
                component_version_detail.ComponentVersionDetail.parse_obj(component_version).dict()
                for component_version in ami.componentVersionDetails
            ]
            if ami.componentVersionDetails
            else None
        )
        additional_attributes["osVersion"] = ami.osVersion
    return additional_attributes


def __update_version(
    uow, new_version_name, fetched_version_distributions, command, additional_attributes, template_path, parameters
):
    current_time = datetime.now(timezone.utc).isoformat()
    for version_distribution in fetched_version_distributions:
        with uow:
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=command.productId.value,
                    versionId=command.versionId.value,
                    awsAccountId=version_distribution.awsAccountId,
                ),
                copiedAmiId=None,
                lastUpdateDate=current_time,
                lastUpdatedBy=command.lastUpdatedBy.value,
                versionName=new_version_name,
                versionDescription=command.versionDescription.value,
                draftTemplateLocation=template_path,
                parameters=[param.dict() for param in parameters],
                status=version.VersionStatus.Updating,
                **additional_attributes,
            )
            uow.commit()


def __publish_version_update_started(message_bus, fetched_version_distributions, command, product_entity):
    for version_distribution in fetched_version_distributions:
        message_bus.publish(
            product_version_update_started.ProductVersionUpdateStarted(
                product_id=command.productId.value,
                version_id=command.versionId.value,
                aws_account_id=version_distribution.awsAccountId,
                product_type=product_entity.productType,
            )
        )
