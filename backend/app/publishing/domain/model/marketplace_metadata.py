from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.publishing.domain.exceptions import domain_exception


class MarketplaceMetadata(BaseModel):
    productCode: Optional[str] = Field(None, title="ProductCode")
    marketplaceProductId: Optional[str] = Field(None, title="MarketplaceProductId")
    subscriptionOwnership: Optional[str] = Field(None, title="SubscriptionOwnership")
    vendorName: Optional[str] = Field(None, title="VendorName")
    regionalAmiIds: Optional[dict[str, str]] = Field(None, title="RegionalAmiIds")
    agreementId: Optional[str] = Field(None, title="AgreementId")
    licenseConfigurationArn: Optional[str] = Field(None, title="LicenseConfigurationArn")
    homeRegion: Optional[str] = Field(None, title="HomeRegion")
    marketplaceListingUrl: Optional[str] = Field(None, title="MarketplaceListingUrl")
    model_config = ConfigDict(extra="ignore")

    def parse_grant_arn_components(self) -> tuple[str, str]:
        if not self.licenseConfigurationArn:
            raise domain_exception.DomainException(
                "Image does not have a license configuration ARN in its marketplace metadata."
            )
        parts = self.licenseConfigurationArn.split(":")
        home_region = parts[3] if len(parts) >= 6 and parts[3] else self.homeRegion
        if not home_region:
            raise domain_exception.DomainException(
                f"Cannot determine home region from license ARN {self.licenseConfigurationArn} "
                "and homeRegion is not set in marketplace metadata."
            )
        return self.licenseConfigurationArn, home_region
