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
    alreadyImported: bool = Field(..., title="AlreadyImported")
    newerVersionAvailable: bool = Field(False, title="NewerVersionAvailable")
    latestAmiId: Optional[str] = Field(None, title="LatestAmiId")
    latestAmiCreationDate: Optional[str] = Field(None, title="LatestAmiCreationDate")
