from pydantic import BaseModel, Field


class MarketplaceImage(BaseModel):
    productId: str = Field(..., title="ProductId")
    name: str = Field(..., title="Name")
    amiId: str = Field(..., title="AmiId")
    platform: str = Field(..., title="Platform")
    architecture: str = Field(..., title="Architecture")
    rootVolumeSize: int = Field(..., title="RootVolumeSize")
