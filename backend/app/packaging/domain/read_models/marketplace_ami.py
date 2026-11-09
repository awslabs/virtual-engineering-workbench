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
