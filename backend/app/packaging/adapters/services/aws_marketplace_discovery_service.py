from typing import Any

import boto3
from aws_lambda_powertools import logging
from botocore.exceptions import ClientError
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_license_manager.client import LicenseManagerClient
from mypy_boto3_marketplace_agreement.client import AgreementServiceClient

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService
from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement
from app.packaging.domain.read_models.marketplace_ami import MarketplaceAmi
from app.packaging.domain.read_models.received_license import ReceivedLicense

logger = logging.Logger()

AMI_STATE_AVAILABLE = "available"
EC2 = "ec2"
GRACEFUL_DEGRADATION_ERROR_CODES = ("AccessDeniedException", "AuthorizationException")
LICENSE_MANAGER = "license-manager"
MARKETPLACE_AGREEMENT = "marketplace-agreement"
MARKETPLACE_REGION = "us-east-1"
MARKETPLACE_CATALOG_NAME = "AWSMarketplace"
MARKETPLACE_OWNER = "aws-marketplace"


class AwsMarketplaceDiscoveryService(MarketplaceAgreementService, MarketplaceAmiService, MarketplaceLicenseService):
    def __init__(self, region: str, boto_session: Any = None):
        self._region = region
        self._boto_session = boto_session

    def __get_agreement_client(self) -> AgreementServiceClient:
        return (
            self._boto_session.client(MARKETPLACE_AGREEMENT, region_name=MARKETPLACE_REGION)
            if self._boto_session
            else boto3.client(MARKETPLACE_AGREEMENT, region_name=MARKETPLACE_REGION)
        )

    def __get_lm_client(self) -> LicenseManagerClient:
        return (
            self._boto_session.client(LICENSE_MANAGER, region_name=self._region)
            if self._boto_session
            else boto3.client(LICENSE_MANAGER, region_name=self._region)
        )

    def __get_ec2_client(self, region: str | None = None) -> EC2Client:
        _region = region or self._region
        return (
            self._boto_session.client(EC2, region_name=_region)
            if self._boto_session
            else boto3.client(EC2, region_name=_region)
        )

    def list_active_agreements(self) -> list[MarketplaceAgreement]:
        agreements = []
        next_token: str | None = None
        try:
            client = self.__get_agreement_client()
            while True:
                kwargs = {
                    "catalog": MARKETPLACE_CATALOG_NAME,
                    "filters": [
                        {"name": "PartyType", "values": ["Acceptor"]},
                        {"name": "AgreementType", "values": ["PurchaseAgreement"]},
                        {"name": "Status", "values": ["ACTIVE"]},
                    ],
                }
                if next_token:
                    kwargs["nextToken"] = next_token
                response = client.search_agreements(**kwargs)
                for a in response.get("agreementViewSummaries", []):
                    resources = a["proposalSummary"]["resources"]
                    product_id = resources[0]["id"] if resources else ""
                    acceptance_time = a.get("acceptanceTime")
                    agreements.append(
                        MarketplaceAgreement(
                            agreementId=a["agreementId"],
                            productId=product_id,
                            offerId=a["proposalSummary"].get("offerId"),
                            status=a["status"],
                            acceptanceDate=acceptance_time.isoformat() if acceptance_time else None,
                        )
                    )
                next_token = response.get("nextToken")
                if not next_token:
                    break
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in GRACEFUL_DEGRADATION_ERROR_CODES:
                logger.warning(
                    "SearchAgreements denied — Marketplace agreement access may not be configured. "
                    "Returning empty agreement list. Error: %s",
                    e,
                )
                return []
            raise adapter_exception.AdapterException(f"Failed to list marketplace agreements: {e}")
        return agreements

    def list_marketplace_amis_by_product_code(self, product_code: str, region: str) -> list[MarketplaceAmi]:
        try:
            response = self.__get_ec2_client(region).describe_images(
                Owners=[MARKETPLACE_OWNER],
                # describe_images hides deprecated images by default, so a
                # subscription whose AMIs are all past their deprecation date
                # looked like a subscription with no AMI at all. Include them and
                # let the caller prefer a supported one.
                IncludeDeprecated=True,
                Filters=[
                    {"Name": "product-code", "Values": [product_code]},
                    {"Name": "state", "Values": [AMI_STATE_AVAILABLE]},
                ],
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to list AMIs for product code {product_code} in {region}: {e}"
            )

        return [self.__to_marketplace_ami(img, region) for img in response.get("Images", [])]

    def list_marketplace_amis_by_product_id(self, product_id: str, region: str) -> list[MarketplaceAmi]:
        try:
            response = self.__get_ec2_client(region).describe_images(
                Owners=[MARKETPLACE_OWNER],
                # See the note in list_marketplace_amis_by_product_code.
                IncludeDeprecated=True,
                Filters=[
                    {"Name": "name", "Values": [f"*{product_id}*"]},
                    {"Name": "state", "Values": [AMI_STATE_AVAILABLE]},
                ],
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to list AMIs for product ID {product_id} in {region}: {e}"
            )

        return [self.__to_marketplace_ami(img, region) for img in response.get("Images", [])]

    def get_regional_ami_ids(self, product_code: str, available_regions: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for region in available_regions:
            try:
                amis = self.list_marketplace_amis_by_product_code(product_code, region)
            except adapter_exception.AdapterException:
                continue
            # A product can publish several AMIs in one region, and describe_images
            # returns them in no defined order, so take the newest rather than
            # whichever arrived last. CreationDate is ISO 8601 and sorts
            # lexicographically; an AMI without one loses to any AMI that has one,
            # and amiId breaks a tie so the result is stable across runs.
            #
            # Deprecated images are now included in the listing, so prefer a
            # supported one and fall back to the newest deprecated image only when
            # every image in the region is deprecated - otherwise adding
            # IncludeDeprecated would have started handing out deprecated AMIs.
            supported = [ami for ami in amis if not ami.deprecated]
            candidates = supported or amis
            newest = max(candidates, key=lambda ami: (ami.creationDate or "", ami.amiId), default=None)
            if newest:
                result[region] = newest.amiId
        return result

    def list_received_licenses(self) -> list[ReceivedLicense]:
        licenses_out: list[ReceivedLicense] = []
        next_token: str | None = None
        try:
            client = self.__get_lm_client()
            while True:
                kwargs = {"NextToken": next_token} if next_token else {}
                response = client.list_received_licenses(**kwargs)
                for lic in response.get("Licenses", []):
                    metadata = {m["Name"]: m.get("Value") for m in lic.get("LicenseMetadata", [])}
                    received_metadata = lic.get("ReceivedMetadata", {})
                    licenses_out.append(
                        ReceivedLicense(
                            licenseArn=lic["LicenseArn"],
                            licenseName=lic["LicenseName"],
                            productName=lic.get("ProductName"),
                            productSku=lic.get("ProductSKU"),
                            issuer=lic["Issuer"]["Name"],
                            status=lic["Status"],
                            sellerOfRecord=metadata.get("sellerOfRecord"),
                            allowedOperations=received_metadata.get("AllowedOperations", []),
                            homeRegion=lic.get("HomeRegion"),
                        )
                    )
                next_token = response.get("NextToken")
                if not next_token:
                    break
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in GRACEFUL_DEGRADATION_ERROR_CODES:
                logger.warning(
                    "ListReceivedLicenses denied — the AWSServiceRoleForMarketplaceLicenseManagement "
                    "service-linked role is likely missing. Returning empty license list. "
                    "To fix: enable License Manager integration in AWS Marketplace settings. Error: %s",
                    e,
                )
                return []
            raise adapter_exception.AdapterException(f"Failed to list received licenses: {e}")
        return licenses_out

    def __to_marketplace_ami(self, img: dict, region: str) -> MarketplaceAmi:
        product_codes = img.get("ProductCodes", [])
        product_code = product_codes[0]["ProductCodeId"] if product_codes else ""
        return MarketplaceAmi(
            amiId=img["ImageId"],
            productCode=product_code,
            platform=img["PlatformDetails"],
            architecture=img["Architecture"],
            state=img["State"],
            name=img.get("Name"),
            description=img.get("Description"),
            region=region,
            creationDate=img.get("CreationDate"),
            deprecationTime=img.get("DeprecationTime"),
        )
