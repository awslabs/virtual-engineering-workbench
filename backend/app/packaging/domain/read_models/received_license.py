from typing import Optional

from pydantic import BaseModel, Field


class ReceivedLicense(BaseModel):
    licenseArn: str = Field(..., title="LicenseArn")
    licenseName: str = Field(..., title="LicenseName")
    productName: Optional[str] = Field(None, title="ProductName")
    productSku: Optional[str] = Field(None, title="ProductSku")
    issuer: str = Field(..., title="Issuer")
    status: str = Field(..., title="Status")
    sellerOfRecord: Optional[str] = Field(None, title="SellerOfRecord")
    allowedOperations: list[str] = Field(default_factory=list, title="AllowedOperations")
    homeRegion: Optional[str] = Field(None, title="HomeRegion")
