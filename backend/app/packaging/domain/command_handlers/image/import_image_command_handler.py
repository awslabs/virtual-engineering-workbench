from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from app.packaging.domain.commands.image import import_image_command
from app.packaging.domain.events.image import image_imported
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.ports import ami_validation_service, image_query_service
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.packaging.domain.value_objects.image.marketplace_metadata_value_object import (
    MarketplaceMetadataValueObject,
    from_dict,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

EC2_TO_VEW_ARCHITECTURE = {
    "arm64": "arm64",
    "arm64_mac": "arm64",
    "i386": "amd64",
    "x86_64": "amd64",
    "x86_64_mac": "amd64",
}


def _map_ec2_architecture(ami_desc: AmiDescription) -> str:
    arch = ami_desc.architecture or ""
    mapped = EC2_TO_VEW_ARCHITECTURE.get(arch)
    if not mapped:
        raise domain_exception.DomainException(
            f"Unsupported architecture: {arch}. Supported: {list(EC2_TO_VEW_ARCHITECTURE.keys())}."
        )
    return mapped


def _validate_and_build_marketplace_metadata(
    command: import_image_command.ImportImageCommand,
    ami_validation_svc: ami_validation_service.AmiValidationService,
    ami_region: str,
) -> MarketplaceMetadataValueObject:
    if not command.marketplaceProductCode:
        raise domain_exception.DomainException("marketplaceProductCode is required for MARKETPLACE_PRODUCT.")
    if not ami_validation_svc.validate_marketplace_product_code(
        command.amiId.value, command.marketplaceProductCode.value
    ):
        raise domain_exception.DomainException(
            f"Product code mismatch: AMI {command.amiId.value} does not have product code {command.marketplaceProductCode.value}."
        )
    return from_dict(
        {
            "productCode": command.marketplaceProductCode.value,
            "subscriptionOwnership": command.subscriptionOwnership or "VEW_MANAGED",
            "regionalAmiIds": command.regionalAmiIds or {ami_region: command.amiId.value},
            "licenseConfigurationArn": command.licenseConfigurationArn,
            "homeRegion": command.homeRegion,
        }
    )


def _describe_and_validate_ami(command, ami_validation_svc, image_source):
    if image_source == ImageSource.MARKETPLACE_PRODUCT:
        ami_desc = ami_validation_svc.describe_marketplace_image(command.amiId.value)
    else:
        ami_desc = ami_validation_svc.describe_image(command.amiId.value)
    if ami_desc.state != "available":
        raise domain_exception.DomainException(f"AMI {command.amiId.value} is not available (state: {ami_desc.state}).")
    if image_source == ImageSource.EXISTING_AMI:
        if not command.imageServiceAccountId:
            raise domain_exception.DomainException(
                "Image Service account ID is not configured; cannot import EXISTING_AMI."
            )
        if ami_desc.ownerId != command.imageServiceAccountId:
            raise domain_exception.DomainException(
                f"AMI {command.amiId.value} is not owned by the Image Service account."
            )
    return ami_desc


def _detect_encryption(ami_description: AmiDescription) -> tuple[Optional[str], Optional[str]]:
    for bdm in ami_description.blockDeviceMappings:
        if bdm.ebs and bdm.ebs.encrypted:
            return ("KMS" if bdm.ebs.kmsKeyId else "AES256", bdm.ebs.kmsKeyId)
    return None, None


def _retire_previous_marketplace_images(
    project_id: str,
    product_code: str,
    new_image_id: str,
    image_qry_srv: image_query_service.ImageQueryService,
    uow: unit_of_work.UnitOfWork,
) -> None:
    current_time = datetime.now(timezone.utc).isoformat()
    for img in image_qry_srv.get_images(project_id):
        if (
            img.imageId != new_image_id
            and img.imageSource == ImageSource.MARKETPLACE_PRODUCT
            and img.status == image.ImageStatus.Created
            and img.marketplaceMetadata
            and img.marketplaceMetadata.get("productCode") == product_code
        ):
            with uow:
                uow.get_repository(image.ImagePrimaryKey, image.Image).update_attributes(
                    image.ImagePrimaryKey(projectId=img.projectId, imageId=img.imageId),
                    status=image.ImageStatus.Retired,
                    lastUpdateDate=current_time,
                )
                uow.commit()


def handle(
    command: import_image_command.ImportImageCommand,
    uow: unit_of_work.UnitOfWork,
    ami_validation_svc: ami_validation_service.AmiValidationService,
    image_qry_srv: image_query_service.ImageQueryService,
    msg_bus: message_bus.MessageBus,
) -> str:
    image_source = command.imageSource.value

    if not command.componentVersionDetails:
        raise domain_exception.DomainException("At least one component version detail is required.")

    if command.imageDescription and len(command.imageDescription) > 500:
        raise domain_exception.DomainException("Image description must be 500 characters or fewer.")

    existing = image_qry_srv.get_image_by_image_upstream_id(command.amiId.value)
    if existing and existing.projectId == command.projectId.value:
        raise domain_exception.DomainException(
            f"AMI {command.amiId.value} is already imported in this project (imageId={existing.imageId})."
        )

    ami_desc = _describe_and_validate_ami(command, ami_validation_svc, image_source)

    marketplace_metadata: Optional[dict] = None
    if image_source == ImageSource.MARKETPLACE_PRODUCT:
        marketplace_metadata = asdict(
            _validate_and_build_marketplace_metadata(command, ami_validation_svc, ami_desc.region)
        )

    encryption_type, kms_key_id = _detect_encryption(ami_desc)

    vew_platform = command.platform.value
    vew_architecture = _map_ec2_architecture(ami_desc)

    current_time = datetime.now(timezone.utc).isoformat()
    image_entity = image.Image(
        projectId=command.projectId.value,
        imageUpstreamId=command.amiId.value,
        status=image.ImageStatus.Created,
        imageSource=ImageSource(image_source),
        imageName=command.imageName.value,
        imageDescription=command.imageDescription,
        platform=vew_platform,
        architecture=vew_architecture,
        osVersion=command.osVersion.value,
        componentVersionDetails=command.componentVersionDetails,
        marketplaceMetadata=marketplace_metadata,
        originalAmiRegion=ami_desc.region,
        encryptionType=encryption_type,
        kmsKeyId=kms_key_id,
        importValidatedAt=current_time,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(image.ImagePrimaryKey, image.Image).add(image_entity)
        uow.commit()

    # Retire older marketplace images with the same product code (same pattern as register_image_command_handler)
    if image_source == ImageSource.MARKETPLACE_PRODUCT and marketplace_metadata:
        _retire_previous_marketplace_images(
            project_id=command.projectId.value,
            product_code=marketplace_metadata["productCode"],
            new_image_id=image_entity.imageId,
            image_qry_srv=image_qry_srv,
            uow=uow,
        )

    msg_bus.publish(
        image_imported.ImageImported(
            projectId=command.projectId.value,
            imageId=image_entity.imageId,
            imageSource=image_source,
            amiId=command.amiId.value,
            imageStatus=image.ImageStatus.Created.value,
            imageName=command.imageName.value,
            imageDescription=command.imageDescription,
            platform=vew_platform,
            architecture=vew_architecture,
            osVersion=command.osVersion.value,
            componentVersionDetails=command.componentVersionDetails,
            marketplaceMetadata=marketplace_metadata,
            createDate=current_time,
        )
    )

    return image_entity.imageId
