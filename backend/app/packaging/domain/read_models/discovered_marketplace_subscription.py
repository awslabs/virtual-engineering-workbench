from typing import Optional

from pydantic import BaseModel, Field


class DiscoveredMarketplaceSubscription(BaseModel):
    productName: str = Field(..., title="ProductName")
    productCode: str = Field(..., title="ProductCode")
    hubRegionAmiId: str = Field(..., title="HubRegionAmiId")
    regionalAmiIds: dict[str, str] = Field(..., title="RegionalAmiIds")
    licenseConfigurationArn: Optional[str] = Field(None, title="LicenseConfigurationArn")
    homeRegion: Optional[str] = Field(None, title="HomeRegion")
    subscriptionOwnership: str = Field(..., title="SubscriptionOwnership")
    # Persist this per-license fact separately from ownership. An externally
    # managed license may still permit CreateGrant when account readiness changes.
    licenseGrantAllowed: bool = Field(False, title="LicenseGrantAllowed")
    alreadyImported: bool = Field(..., title="AlreadyImported")
    newerVersionAvailable: bool = Field(False, title="NewerVersionAvailable")
    # True when the AMI this subscription would import is past its deprecation
    # date, which happens when the product publishes no supported image.
    deprecated: bool = Field(False, title="Deprecated")
    deprecationTime: Optional[str] = Field(None, title="DeprecationTime")
    latestAmiId: Optional[str] = Field(None, title="LatestAmiId")
    latestAmiCreationDate: Optional[str] = Field(None, title="LatestAmiCreationDate")
