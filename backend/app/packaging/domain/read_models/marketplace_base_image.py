from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceBaseImage(BaseModel):
    """A subscribed AWS Marketplace AMI that a recipe version can build on."""

    # Marketplace product (subscription path) or, for an imported AWS-published image, None.
    productId: Optional[str] = Field(None, title="ProductId")
    # The imported image the AMI comes from (AWS-published path), else None.
    imageId: Optional[str] = Field(None, title="ImageId")
    productName: str = Field(..., title="ProductName")
    productCode: Optional[str] = Field(None, title="ProductCode")
    amiId: str = Field(..., title="AmiId")
    platform: str = Field(..., title="Platform")
    architecture: str = Field(..., title="Architecture")
    rootVolumeSize: int = Field(..., title="RootVolumeSize")
    licenseConfigurationArn: Optional[str] = Field(None, title="LicenseConfigurationArn")
    homeRegion: Optional[str] = Field(None, title="HomeRegion")
    subscriptionOwnership: str = Field(..., title="SubscriptionOwnership")
    # Whether the hub's licence allows CreateGrant. Publishing needs it to turn an Externally
    # Managed parent into a grant the hub creates, as it does for an imported Marketplace AMI.
    licenseGrantAllowed: bool = Field(False, title="LicenseGrantAllowed")
    # Instance types the product launches on; empty when unknown (then nothing is restricted).
    supportedInstanceTypes: list[str] = Field(default_factory=list, title="SupportedInstanceTypes")

    def to_parent_image_marketplace_metadata(self) -> dict:
        """What a recipe version keeps about its Marketplace parent, so that images built from it
        can carry the license on to publishing. No regional AMI IDs: the built image is our own AMI."""
        return {
            "marketplaceProductId": self.productId,
            "productCode": self.productCode,
            "licenseConfigurationArn": self.licenseConfigurationArn,
            "homeRegion": self.homeRegion,
            "subscriptionOwnership": self.subscriptionOwnership,
            "licenseGrantAllowed": self.licenseGrantAllowed,
            "rootVolumeSize": self.rootVolumeSize,
        }
