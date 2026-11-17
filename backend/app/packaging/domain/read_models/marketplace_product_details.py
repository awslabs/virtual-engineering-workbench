from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceProductDetails(BaseModel):
    productId: str = Field(..., title="ProductId")
    productName: str = Field(..., title="ProductName")
    shortDescription: Optional[str] = Field(None, title="ShortDescription")
    publisher: str = Field(..., title="Publisher")
