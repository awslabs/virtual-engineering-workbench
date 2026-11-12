import enum
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import image_service, license_manager_service, shared_amis_query_service
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    product_id_value_object,
    product_type_value_object,
    region_value_object,
    version_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ImageSource(str, enum.Enum):
    MARKETPLACE_PRODUCT = "MARKETPLACE_PRODUCT"


class SubscriptionOwnership(str, enum.Enum):
    VEW_MANAGED = "VEW_MANAGED"
    EXTERNALLY_MANAGED = "EXTERNALLY_MANAGED"


class ShareAmiDecision(str, enum.Enum):
    Done = "DONE"
    Share = "SHARE"
    Copy = "COPY"
    NotRequired = "NOT_REQUIRED"
    LicenseGrant = "LICENSE_GRANT"
    VerifyExternalGrant = "VERIFY_EXTERNAL_GRANT"

    def __str__(self):
        return str(self.value)


@dataclass(frozen=True)
class ShareAmiDecisionResult:
    decision: ShareAmiDecision
    region: str
    original_ami_id: str
    copied_ami_id: typing.Optional[str]
    # Only set for marketplace products: the sharing step function needs the
    # licence identity to create or verify a License Manager grant, and a
    # marketplace AMI is never copied, so copied_ami_id stays None.
    image_id: typing.Optional[str] = None
    project_id: typing.Optional[str] = None
    license_arn: typing.Optional[str] = None
    home_region: typing.Optional[str] = None
    grant_name: typing.Optional[str] = None


class SharedAMIsDomainQueryService:
    def __init__(
        self,
        unit_of_work: unit_of_work.UnitOfWork,
        image_svc: image_service.ImageService,
        shared_amis_qry_svc: shared_amis_query_service.SharedAMIsQueryService,
        default_original_ami_region: str,
        # Optional so the decision still works without it; only the
        # externally-managed upgrade below consults License Manager.
        license_manager_svc: license_manager_service.LicenseManagerService | None = None,
    ) -> None:
        self._uow = unit_of_work
        self._image_svc = image_svc
        self._shared_amis_qry_svc = shared_amis_qry_svc
        self._default_original_ami_region = default_original_ami_region
        self._license_manager_svc = license_manager_svc

    # A marketplace subscription VEW owns is licensed by granting the spoke
    # account a share of the hub's licence; one the customer already owns is
    # only verified, because VEW holds no licence to grant.
    _MARKETPLACE_DECISION_BY_OWNERSHIP = {
        SubscriptionOwnership.VEW_MANAGED: ShareAmiDecision.LicenseGrant,
        SubscriptionOwnership.EXTERNALLY_MANAGED: ShareAmiDecision.VerifyExternalGrant,
    }

    @staticmethod
    def _license_location(version_entity: version.Version) -> tuple[str | None, str | None]:
        """The licence ARN and its home region for a marketplace version.

        Older records predate homeRegion, so fall back to the region segment of the
        licence ARN: arn:aws:license-manager:<region>:<account>:...
        """
        metadata = version_entity.marketplaceMetadata
        license_arn = metadata.licenseConfigurationArn if metadata else None
        home_region = metadata.homeRegion if metadata else None
        if not home_region and license_arn:
            parts = license_arn.split(":")
            if len(parts) >= 6 and parts[3]:
                home_region = parts[3]
        return license_arn, home_region

    def _upgrade_external_grant_decision(
        self,
        version_entity: version.Version,
        decision: ShareAmiDecision,
        spoke_account_id: str,
    ) -> ShareAmiDecision:
        """Turn a verify-only decision into a real grant when the hub can make one.

        An externally-managed subscription means the customer owns the licence, so VEW
        normally only verifies that the spoke already has a grant. But when the spoke
        has no grant AND License Manager's organization integration is switched on, the
        hub can distribute one itself - which is the difference between a workbench that
        launches and one that fails with no licence. Without this the decision was
        always verify-only and such a launch could never succeed.
        """
        if decision != ShareAmiDecision.VerifyExternalGrant or self._license_manager_svc is None:
            return decision

        license_arn, home_region = self._license_location(version_entity)
        if not license_arn or not home_region:
            return decision

        if self._license_manager_svc.has_active_received_grant(
            license_arn=license_arn, spoke_account_id=spoke_account_id, home_region=home_region
        ):
            # Already granted; there is nothing to distribute, only to verify.
            return decision

        if self._license_manager_svc.can_distribute_license():
            return ShareAmiDecision.LicenseGrant
        return decision

    def _marketplace_decision(
        self,
        version_entity: version.Version,
        decision: ShareAmiDecision,
    ) -> ShareAmiDecisionResult:
        license_arn, home_region = self._license_location(version_entity)

        # A marketplace product publishes a different AMI id per region, so the
        # spoke's own region decides which one to launch. Fall back to the
        # recorded original when the product lists no AMI for that region.
        metadata = version_entity.marketplaceMetadata
        regional_ami_ids = metadata.regionalAmiIds if metadata else None
        spoke_region = version_entity.region
        regional_ami_id = (
            regional_ami_ids.get(spoke_region, version_entity.originalAmiId)
            if regional_ami_ids
            else version_entity.originalAmiId
        )

        return ShareAmiDecisionResult(
            decision=decision,
            region=spoke_region,
            # The grant is recorded against the REGISTERED AMI - the image the
            # project imported, which is what the publishing AMIs table is keyed by
            # and what create_license_grant authorizes against. Passing the regional
            # id here made that lookup miss, so every Marketplace grant would be
            # rejected as "not part of project".
            original_ami_id=version_entity.originalAmiId,
            copied_ami_id=None,
            # The regional image is the one the spoke launches, so the launch
            # permission check and the recorded copiedAmiId use it.
            image_id=regional_ami_id,
            project_id=getattr(version_entity, "projectId", None),
            license_arn=license_arn,
            home_region=home_region,
            grant_name=f"VEW-{version_entity.productId}-{version_entity.awsAccountId}",
        )

    def make_share_ami_decision(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject,
        aws_account_id: aws_account_id_value_object.AWSAccountIDValueObject,
        product_type: product_type_value_object.ProductTypeValueObject,
    ) -> ShareAmiDecisionResult:
        with self._uow:
            version_entity: version.Version = self._uow.get_repository(version.VersionPrimaryKey, version.Version).get(
                pk=version.VersionPrimaryKey(
                    productId=product_id.value, versionId=version_id.value, awsAccountId=aws_account_id.value
                )
            )
            # lets add a skip decision is its a container product type
            if product_type.value == product.ProductType.Container:
                return ShareAmiDecisionResult(
                    decision=ShareAmiDecision.NotRequired,
                    region=version_entity.region,
                    original_ami_id="",
                    copied_ami_id="",
                )

            # A marketplace AMI is already published to the spoke's region by the
            # seller, so it is never shared or copied; the decision is about the
            # licence instead. Unknown ownership falls through to AMI sharing.
            if version_entity.imageSource == ImageSource.MARKETPLACE_PRODUCT:
                subscription_ownership = (
                    version_entity.marketplaceMetadata.subscriptionOwnership
                    if version_entity.marketplaceMetadata
                    else ""
                )
                marketplace_decision = self._MARKETPLACE_DECISION_BY_OWNERSHIP.get(subscription_ownership)
                if marketplace_decision is not None:
                    marketplace_decision = self._upgrade_external_grant_decision(
                        version_entity, marketplace_decision, aws_account_id.value
                    )
                    return self._marketplace_decision(version_entity, marketplace_decision)

        # Records written before region joined the key are still found by this query, so no migration is needed.
        shared_ami_entity = next(
            (
                ami
                for ami in self._shared_amis_qry_svc.get_shared_amis(original_ami_id=version_entity.originalAmiId)
                if ami.awsAccountId == aws_account_id.value and ami.region == version_entity.region
            ),
            None,
        )

        # Make the decision
        copied_ami_id = None
        if shared_ami_entity:
            decision = ShareAmiDecision.Done
            copied_ami_id = shared_ami_entity.copiedAmiId
        elif version_entity.region == self._default_original_ami_region:
            decision = ShareAmiDecision.Share
        elif version_entity.region != self._default_original_ami_region:
            decision = ShareAmiDecision.Copy
        else:
            raise domain_exception.DomainException("Unsupported logic when making the decision")

        return ShareAmiDecisionResult(
            decision=decision,
            region=version_entity.region,
            original_ami_id=version_entity.originalAmiId,
            copied_ami_id=copied_ami_id,
        )

    def verify_copy(
        self,
        region: region_value_object.RegionValueObject,
        copied_ami_id: ami_id_value_object.AmiIdValueObject,
    ) -> bool:
        copied_ami_status = self._image_svc.get_copied_ami_status(copied_ami_id.value, region.value)
        if copied_ami_status == "available":
            return True
        elif copied_ami_status == "pending":
            return False
        else:
            raise domain_exception.DomainException(f"Unsupported copied ami status {copied_ami_status}")
