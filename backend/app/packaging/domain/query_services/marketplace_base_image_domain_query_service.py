import logging

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image as image_model
from app.packaging.domain.model.image.image_constants import ImageSource, SubscriptionOwnership
from app.packaging.domain.ports.ami_validation_service import AmiValidationService
from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_base_image_query_service import MarketplaceBaseImageQueryService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService
from app.packaging.domain.ports.marketplace_offer_service import MarketplaceOfferService
from app.packaging.domain.ports.parameter_service import ParameterDefinitionService
from app.packaging.domain.query_services.marketplace_subscription_domain_query_service import (
    ACTIVE_LICENSE_STATUSES,
    CREATE_GRANT,
    classify_ownership,
    to_recipe_architecture,
    to_recipe_platform,
)
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.packaging.domain.read_models.marketplace_base_image import MarketplaceBaseImage
from app.packaging.domain.read_models.received_license import ReceivedLicense

# Public SSM parameter AWS Marketplace keeps pointing at the latest AMI of a product, per region.
AMI_ALIAS_PARAMETER_NAME = "/aws/service/marketplace/{product_id}/latest"
# Recipes, recipe testing and the product templates all map the root volume at this device.
ROOT_DEVICE_NAME = "/dev/sda1"


class MarketplaceBaseImageDomainQueryService(MarketplaceBaseImageQueryService):
    """Resolves subscribed Marketplace AMI products to recipe parent images.

    Uses the same subscription view as Marketplace discovery and Import AMI: a product counts as
    subscribed when the hub has an active received license for it. The AMI is resolved and described
    in the AMI factory account, where EC2 Image Builder builds the recipe.
    """

    def __init__(
        self,
        license_service: MarketplaceLicenseService,
        agreement_service: MarketplaceAgreementService,
        ami_service: MarketplaceAmiService,
        parameter_service: ParameterDefinitionService,
        ami_validation_service: AmiValidationService,
        region: str,
        logger: logging.Logger,
        offer_service: MarketplaceOfferService | None = None,
        image_query_service: ImageQueryService | None = None,
    ) -> None:
        self._license_service = license_service
        self._agreement_service = agreement_service
        self._ami_service = ami_service
        self._parameter_service = parameter_service
        self._ami_validation_service = ami_validation_service
        self._region = region
        self._logger = logger
        self._offer_service = offer_service
        self._image_query_service = image_query_service

    def get_base_image(self, product_id: str) -> MarketplaceBaseImage:
        license = self._get_active_license(product_id)
        ami_id = self._resolve_ami_id(product_id)
        ami = self._describe(product_id, ami_id)

        architecture = to_recipe_architecture(ami.architecture)
        if not architecture:
            raise domain_exception.DomainException(
                f"Product {product_id} has an unsupported architecture {ami.architecture}."
            )
        root_volume_size = self._get_root_volume_size(product_id, ami)

        agreement = next(
            (a for a in self._agreement_service.list_active_agreements() if a.productId == product_id), None
        )
        ownership = classify_ownership(license, agreement)

        return MarketplaceBaseImage(
            productId=product_id,
            productName=license.productName or ami.name or product_id,
            productCode=ami.productCodes[0].productCodeId if ami.productCodes else None,
            amiId=ami.amiId,
            platform=to_recipe_platform(ami.platform),
            architecture=architecture,
            rootVolumeSize=root_volume_size,
            licenseConfigurationArn=license.licenseArn,
            homeRegion=license.homeRegion,
            subscriptionOwnership=ownership.value,
            licenseGrantAllowed=CREATE_GRANT in license.allowedOperations,
            supportedInstanceTypes=(
                self._offer_service.list_supported_instance_types(product_id) if self._offer_service else []
            ),
        )

    def get_imported_base_image(self, project_id: str, image_id: str) -> MarketplaceBaseImage:
        imported = self._image_query_service.get_image(project_id, image_id) if self._image_query_service else None
        if (
            not imported
            or imported.imageSource != ImageSource.AWS_PUBLISHED_AMI
            or imported.status != image_model.ImageStatus.Created
            or not imported.imageUpstreamId
        ):
            raise domain_exception.DomainException(
                f"Image {image_id} is not an imported AWS-published image available in this project."
            )
        ami = self._describe(image_id, imported.imageUpstreamId)
        architecture = to_recipe_architecture(ami.architecture)
        if not architecture:
            raise domain_exception.DomainException(
                f"Image {image_id} has an unsupported architecture {ami.architecture}."
            )
        return MarketplaceBaseImage(
            imageId=image_id,
            productName=imported.imageName or image_id,
            productCode=ami.productCodes[0].productCodeId if ami.productCodes else None,
            amiId=ami.amiId,
            platform=to_recipe_platform(ami.platform),
            architecture=architecture,
            rootVolumeSize=self._get_root_volume_size(image_id, ami),
            # AWS is the seller of record: the license comes with the EC2 instance, nothing to grant.
            subscriptionOwnership=SubscriptionOwnership.AWS_MANAGED.value,
        )

    def _get_active_license(self, product_id: str) -> ReceivedLicense:
        license = next(
            (
                lic
                for lic in self._license_service.list_received_licenses()
                if lic.productSku == product_id and lic.status in ACTIVE_LICENSE_STATUSES
            ),
            None,
        )
        if not license:
            raise domain_exception.DomainException(
                f"Product {product_id} is not an AWS Marketplace product with an active subscription."
            )
        return license

    def _resolve_ami_id(self, product_id: str) -> str:
        try:
            return self._parameter_service.get_parameter_value(AMI_ALIAS_PARAMETER_NAME.format(product_id=product_id))
        except Exception as e:
            # Not every product publishes the alias; fall back to the newest AMI that names the product.
            self._logger.info(f"No AMI alias for {product_id}, falling back to the AMI name search: {e}")

        amis = [a for a in self._ami_service.list_marketplace_amis_by_product_id(product_id, self._region) if a.amiId]
        if not amis:
            raise domain_exception.DomainException(f"Product {product_id} has no AMI available in {self._region}.")
        return max(amis, key=lambda a: a.creationDate or "").amiId

    def _describe(self, product_id: str, ami_id: str) -> AmiDescription:
        try:
            return self._ami_validation_service.describe_image(ami_id)
        except Exception as e:
            self._logger.warning(f"Could not describe AMI {ami_id} of {product_id}: {e}")
            raise domain_exception.DomainException(
                f"AMI {ami_id} of {product_id} is not available to the image factory."
            ) from e

    @staticmethod
    def _get_root_volume_size(product_id: str, ami: AmiDescription) -> int:
        root = next((m for m in ami.blockDeviceMappings if m.deviceName == ROOT_DEVICE_NAME), None)
        if not root or not root.ebs or not root.ebs.volumeSize:
            raise domain_exception.DomainException(
                f"{product_id} does not use {ROOT_DEVICE_NAME} as its root volume, "
                "which recipes need to size the root volume."
            )
        return root.ebs.volumeSize
