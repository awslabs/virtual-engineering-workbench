from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceAmi(BaseModel):
    amiId: str = Field(..., title="AmiId")
    productCode: str = Field(..., title="ProductCode")
    platform: Optional[str] = Field(None, title="Platform")
    architecture: Optional[str] = Field(None, title="Architecture")
    state: str = Field(..., title="State")
    name: Optional[str] = Field(None, title="Name")
    description: Optional[str] = Field(None, title="Description")
    region: str = Field(..., title="Region")
    creationDate: Optional[str] = Field(None, title="CreationDate")
    # EC2 reports DeprecationTime on a deprecated image. Carried so a caller can
    # prefer a supported AMI and warn when only deprecated ones remain.
    deprecationTime: Optional[str] = Field(None, title="DeprecationTime")

    @property
    def deprecated(self) -> bool:
        if not self.deprecationTime:
            return False
        deprecation_time = datetime.fromisoformat(self.deprecationTime.replace("Z", "+00:00"))
        if deprecation_time.tzinfo is None:
            deprecation_time = deprecation_time.replace(tzinfo=timezone.utc)
        return deprecation_time <= datetime.now(timezone.utc)
