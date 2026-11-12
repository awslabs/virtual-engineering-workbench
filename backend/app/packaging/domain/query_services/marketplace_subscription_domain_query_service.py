import logging

from app.packaging.domain.model.image.image_constants import ImageSource, SubscriptionOwnership
from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService
from app.packaging.domain.ports.marketplace_subscription_query_service import MarketplaceSubscriptionQueryService
from app.packaging.domain.ports.org_integration_service import OrgIntegrationService
from app.packaging.domain.read_models.discovered_marketplace_subscription import DiscoveredMarketplaceSubscription
from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement
from app.packaging.domain.read_models.marketplace_ami import MarketplaceAmi
from app.packaging.domain.read_models.received_license import ReceivedLicense
from app.packaging.domain.value_objects.shared import project_id_value_object

ACTIVE_LICENSE_STATUSES = ("AVAILABLE", "ACTIVE")
CREATE_GRANT = "CreateGrant"


class MarketplaceSubscriptionDomainQueryService(MarketplaceSubscriptionQueryService):
    def __init__(
        self,
        agreement_service: MarketplaceAgreementService,
        ami_service: MarketplaceAmiService,
        license_service: MarketplaceLicenseService,
        org_integration_service: OrgIntegrationService,
        image_qry_svc: ImageQueryService,
        available_regions: list[str],
        logger: logging.Logger,
    ) -> None:
        self._agreement_service = agreement_service
        self._ami_service = ami_service
        self._license_service = license_service
        self._org_integration_service = org_integration_service
        self._image_qry_svc = image_qry_svc
        self._available_regions = available_regions
        self._logger = logger

    def discover(
        self, project_id: project_id_value_object.ProjectIdValueObject
    ) -> list[DiscoveredMarketplaceSubscription]:
        agreements = self._agreement_service.list_active_agreements()
        licenses = self._license_service.list_received_licenses()
        active_licenses = [lic for lic in licenses if lic.status in ACTIVE_LICENSE_STATUSES]

        if not agreements and not active_licenses:
            return []

        hub_region = self._available_regions[0] if self._available_regions else None
        if not hub_region:
            return []

        agreement_by_product_code = self._index_by_ec2_product_code(
            [(a.productId, a) for a in agreements if a.productId], hub_region
        )
        license_by_product_code = self._index_by_ec2_product_code(
            [(lic.productSku, lic) for lic in active_licenses if lic.productSku], hub_region
        )

        if not license_by_product_code:
            return []

        imported_product_codes = self._get_imported_product_codes(project_id)
        imported_ami_ids = self._get_imported_ami_ids(project_id)
        org_integration_active = self._org_integration_service.is_license_manager_org_integration_active()

        result: list[DiscoveredMarketplaceSubscription] = []
        for product_code, (hub_ami, lic) in license_by_product_code.items():
            agreement_entry = agreement_by_product_code.get(product_code)
            agreement = agreement_entry[1] if agreement_entry else None
            regional_ami_ids = {hub_ami.region: hub_ami.amiId}
            missing_regions = [r for r in self._available_regions if r not in regional_ami_ids]
            if missing_regions:
                regional_ami_ids.update(self._ami_service.get_regional_ami_ids(product_code, missing_regions))

            newer_version_available, latest_ami_id, latest_ami_creation_date = self._check_for_newer_version(
                product_code, hub_region, imported_product_codes, imported_ami_ids
            )

            result.append(
                self._build_subscription(
                    hub_ami=hub_ami,
                    license=lic,
                    agreement=agreement,
                    org_integration_active=org_integration_active,
                    regional_ami_ids=regional_ami_ids,
                    imported_product_codes=imported_product_codes,
                    newer_version_available=newer_version_available,
                    latest_ami_id=latest_ami_id,
                    latest_ami_creation_date=latest_ami_creation_date,
                )
            )
        return result

    def _check_for_newer_version(
        self,
        product_code: str,
        hub_region: str,
        imported_product_codes: set[str],
        imported_ami_ids: set[str],
    ) -> tuple[bool, str | None, str | None]:
        if product_code not in imported_product_codes:
            return False, None, None
        all_amis = self._ami_service.list_marketplace_amis_by_product_code(product_code, hub_region)
        dated_amis = [a for a in all_amis if a.creationDate]
        if not dated_amis:
            return False, None, None
        latest = max(dated_amis, key=lambda a: a.creationDate)
        if latest.amiId not in imported_ami_ids:
            return True, latest.amiId, latest.creationDate
        return False, None, None

    def _index_by_ec2_product_code(
        self, items: list[tuple[str, object]], hub_region: str
    ) -> dict[str, tuple[MarketplaceAmi, object]]:
        index: dict[str, tuple[MarketplaceAmi, object]] = {}
        for product_id, item in items:
            hub_ami = self._lookup_hub_ami_by_product_id(product_id, hub_region)
            if not hub_ami or not hub_ami.productCode:
                self._logger.warning(f"No AMI found for product ID {product_id} in hub region {hub_region}")
                continue
            index.setdefault(hub_ami.productCode, (hub_ami, item))
        return index

    def _lookup_hub_ami_by_product_id(self, product_id: str, hub_region: str) -> MarketplaceAmi | None:
        """The AMI to import for a product, in the hub region.

        describe_images returns images in no defined order, so amis[0] picked an
        arbitrary one - and now that deprecated images are included, that could be a
        deprecated AMI while a supported one existed. Prefer the newest supported
        image, and only fall back to the newest deprecated one when every image is
        deprecated, so an older subscription still resolves to something.
        """
        amis = self._ami_service.list_marketplace_amis_by_product_id(product_id, hub_region)
        if not amis:
            return None

        def newest(candidates: list[MarketplaceAmi]) -> MarketplaceAmi:
            # CreationDate is ISO 8601 and sorts lexicographically; an image without
            # one loses to any image that has one, and amiId breaks a tie so the
            # result is stable across runs.
            return max(candidates, key=lambda ami: (ami.creationDate or "", ami.amiId))

        supported = [ami for ami in amis if not ami.deprecated]
        return newest(supported) if supported else newest(amis)

    def _get_imported_product_codes(self, project_id: project_id_value_object.ProjectIdValueObject) -> set[str]:
        return {
            img.marketplaceMetadata["productCode"]
            for img in self._image_qry_svc.get_images(project_id.value)
            if img.imageSource == ImageSource.MARKETPLACE_PRODUCT
            and img.marketplaceMetadata
            and img.marketplaceMetadata.get("productCode")
        }

    def _get_imported_ami_ids(self, project_id: project_id_value_object.ProjectIdValueObject) -> set[str]:
        return {
            img.imageUpstreamId
            for img in self._image_qry_svc.get_images(project_id.value)
            if img.imageSource == ImageSource.MARKETPLACE_PRODUCT and img.imageUpstreamId
        }

    @staticmethod
    def _classify(
        license: ReceivedLicense, agreement: MarketplaceAgreement | None, org_integration_active: bool
    ) -> SubscriptionOwnership:
        if CREATE_GRANT in license.allowedOperations and agreement is not None and org_integration_active:
            return SubscriptionOwnership.VEW_MANAGED
        return SubscriptionOwnership.EXTERNALLY_MANAGED

    @staticmethod
    def _build_subscription(
        hub_ami: MarketplaceAmi,
        license: ReceivedLicense,
        agreement: MarketplaceAgreement | None,
        org_integration_active: bool,
        regional_ami_ids: dict[str, str],
        imported_product_codes: set,
        newer_version_available: bool = False,
        latest_ami_id: str | None = None,
        latest_ami_creation_date: str | None = None,
    ) -> DiscoveredMarketplaceSubscription:
        ownership = MarketplaceSubscriptionDomainQueryService._classify(license, agreement, org_integration_active)
        return DiscoveredMarketplaceSubscription(
            productName=license.productName or hub_ami.name or "",
            productCode=hub_ami.productCode,
            hubRegionAmiId=hub_ami.amiId,
            regionalAmiIds=regional_ami_ids,
            licenseConfigurationArn=license.licenseArn,
            homeRegion=license.homeRegion,
            subscriptionOwnership=ownership.value,
            alreadyImported=hub_ami.productCode in imported_product_codes,
            newerVersionAvailable=newer_version_available,
            latestAmiId=latest_ami_id,
            latestAmiCreationDate=latest_ami_creation_date,
        )
