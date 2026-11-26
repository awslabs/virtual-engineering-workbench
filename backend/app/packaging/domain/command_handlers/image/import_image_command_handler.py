import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from app.packaging.domain.commands.image import import_image_command
from app.packaging.domain.events.image import image_imported
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image
from app.packaging.domain.model.image.image_constants import (
    AWS_PUBLISHED_AMI_OWNER_IDS,
    ImageSource,
    SubscriptionOwnership,
)
from app.packaging.domain.ports import ami_validation_service, image_query_service
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.query_services.aws_published_ami_domain_query_service import (
    AwsPublishedAmiDomainQueryService,
    AwsPublishedAmiResolutionResult,
)
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.packaging.domain.value_objects.image.marketplace_metadata_value_object import (
    MarketplaceMetadataValueObject,
    from_dict,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

logger = logging.getLogger(__name__)

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
            "licenseGrantAllowed": command.licenseGrantAllowed,
        }
    )


def _resolve_aws_published_import(
    command: import_image_command.ImportImageCommand,
    aws_published_qry_svc: Optional[AwsPublishedAmiDomainQueryService],
) -> AwsPublishedAmiResolutionResult:
    """Resolve the listing again and confirm it offers the AMI being imported.

    The caller sends an AMI id, and for this source there is no Image Service
    ownership check to fall back on, so the id is only trusted when the
    server's own resolution of the listing offers it. That resolution applies
    the product-code match, the vendor owner and the billing code, so a
    product-coded AMI from another seller, a private rebuild of a Marketplace
    instance, or a BYOL variant of the same OS are all refused here.
    """
    if aws_published_qry_svc is None:
        raise domain_exception.DomainException("AWS-published AMI import is not available in this deployment.")
    if not command.marketplaceListingId:
        raise domain_exception.DomainException("marketplaceMetadata.listingId is required for AWS_PUBLISHED_AMI.")

    resolution = aws_published_qry_svc.resolve_listing(command.projectId, command.marketplaceListingId)
    offered = {c.amiId for c in resolution.candidates}
    if resolution.resolved:
        offered.add(resolution.resolved.amiId)
    if command.amiId.value not in offered:
        raise domain_exception.DomainException(
            f"AMI {command.amiId.value} is not offered by Marketplace listing {command.marketplaceListingId}."
        )
    return resolution


def _build_aws_published_metadata(
    command: import_image_command.ImportImageCommand,
    ami_desc: AmiDescription,
    agreement_svc: Optional[MarketplaceAgreementService],
    marketplace_product_id: str,
) -> dict:
    """Metadata for an AWS-published AMI.

    An AMI that carries a Marketplace product code is licensed through an
    agreement, so ``productCode`` and ``subscriptionOwnership=VEW_MANAGED``
    are recorded and the agreement id is looked up for convenience. An
    agreement names its Marketplace product, not the EC2 product code, so the
    lookup matches on the product id of the resolved listing. An AMI
    with no product code is licensed through the EC2 billing code, has no
    agreement to point at, and is recorded as ``AWS_MANAGED`` so a later
    reader does not mistake the empty fields for a broken import.

    ``regionalAmiIds`` holds only the region the AMI was resolved in. The
    caller's own list is ignored, because those ids end up in the published
    product template and nothing has checked them.
    """
    product_codes = ami_desc.productCodes or []
    product_code = product_codes[0].productCodeId if product_codes else None

    agreement_id: Optional[str] = None
    if product_code and agreement_svc is not None:
        try:
            for agreement in agreement_svc.list_active_agreements():
                if agreement.productId == marketplace_product_id:
                    agreement_id = agreement.agreementId
                    break
        except Exception:
            # Best effort: productCode is enough to find the agreement later,
            # and an auxiliary lookup must not fail the import.
            logger.warning("Could not look up the agreement for product code %s", product_code, exc_info=True)
            agreement_id = None

    subscription_ownership = (
        SubscriptionOwnership.VEW_MANAGED.value if product_code else SubscriptionOwnership.AWS_MANAGED.value
    )

    return {
        "productCode": product_code,
        "subscriptionOwnership": subscription_ownership,
        "regionalAmiIds": {ami_desc.region: command.amiId.value},
        "licenseConfigurationArn": None,
        "homeRegion": command.homeRegion,
        "agreementId": agreement_id,
    }


def _describe_and_validate_ami(command, ami_validation_svc, image_source):
    if image_source in (ImageSource.MARKETPLACE_PRODUCT, ImageSource.AWS_PUBLISHED_AMI):
        # Both are third-party-owned images, so the Image Service account
        # listing cannot describe them. For AWS_PUBLISHED_AMI the describe
        # also reports the ProductCodes field, which drives the owner check
        # below.
        ami_desc = ami_validation_svc.describe_marketplace_image(command.amiId.value)
    else:
        ami_desc = ami_validation_svc.describe_image(command.amiId.value)
    if ami_desc.state != "available":
        raise domain_exception.DomainException(f"AMI {command.amiId.value} is not available (state: {ami_desc.state}).")
    if image_source == ImageSource.AWS_PUBLISHED_AMI:
        # Second belt behind the resolution check in
        # ``_resolve_aws_published_import``. An AMI with no product code is
        # identified by its owner and name alone, so require a known vendor
        # owner; a product-coded AMI is identified by the code itself.
        if not ami_desc.productCodes and ami_desc.ownerId not in AWS_PUBLISHED_AMI_OWNER_IDS:
            raise domain_exception.DomainException(
                f"AMI {command.amiId.value} is not published by a recognised AWS Marketplace vendor."
            )
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


# An imported AMI is one image per AMI id across ALL projects: packaging's upstream-id
# lookup and publishing's AMI read model (keyed by AMI id alone, its projectId used to
# authorize licence grants) both assume it. A second project importing the same AMI
# would take that read-model row over, so the first project's grants would fail and
# the AMI would drop out of its list. Only an image that never finished (Failed), or
# one marked Deleted, releases the AMI. Retired still holds it: published versions
# may still use the AMI, and the read-model row stays.
_STATUSES_RELEASING_AMI = {image.ImageStatus.Deleted, image.ImageStatus.Failed}


def _reject_already_imported_ami(
    command: import_image_command.ImportImageCommand,
    image_qry_srv: image_query_service.ImageQueryService,
) -> None:
    for existing in image_qry_srv.get_images_by_image_upstream_id(command.amiId.value):
        if existing.projectId == command.projectId.value:
            raise domain_exception.DomainException(
                f"AMI {command.amiId.value} is already imported in this project (imageId={existing.imageId})."
            )
        if existing.status not in _STATUSES_RELEASING_AMI:
            # Do not name the other project: the caller may not be a member of it.
            raise domain_exception.DomainException(
                f"AMI {command.amiId.value} is already imported in another project. "
                "An AMI can be imported into one project only."
            )


def handle(
    command: import_image_command.ImportImageCommand,
    uow: unit_of_work.UnitOfWork,
    ami_validation_svc: ami_validation_service.AmiValidationService,
    image_qry_srv: image_query_service.ImageQueryService,
    msg_bus: message_bus.MessageBus,
    agreement_svc: Optional[MarketplaceAgreementService] = None,
    aws_published_qry_svc: Optional[AwsPublishedAmiDomainQueryService] = None,
) -> str:
    image_source = command.imageSource.value

    if not command.componentVersionDetails:
        raise domain_exception.DomainException("At least one component version detail is required.")

    if command.imageDescription and len(command.imageDescription) > 500:
        raise domain_exception.DomainException("Image description must be 500 characters or fewer.")

    _reject_already_imported_ami(command, image_qry_srv)

    if image_source == ImageSource.AWS_PUBLISHED_AMI:
        resolution = _resolve_aws_published_import(command, aws_published_qry_svc)

    ami_desc = _describe_and_validate_ami(command, ami_validation_svc, image_source)

    marketplace_metadata: Optional[dict] = None
    if image_source == ImageSource.MARKETPLACE_PRODUCT:
        marketplace_metadata = asdict(
            _validate_and_build_marketplace_metadata(command, ami_validation_svc, ami_desc.region)
        )
    elif image_source == ImageSource.AWS_PUBLISHED_AMI:
        marketplace_metadata = _build_aws_published_metadata(command, ami_desc, agreement_svc, resolution.productId)

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
