from typing import Optional

from pydantic import BaseModel, Field


class LicenseDetails(BaseModel):
    licenseArn: str = Field(..., title="LicenseArn")
    licenseName: str = Field(..., title="LicenseName")
    productName: Optional[str] = Field(None, title="ProductName")
    status: str = Field(..., title="Status")
    homeRegion: str = Field(..., title="HomeRegion")
