from typing import Optional

from pydantic import BaseModel, Field


class ProductVersionAmiShared(BaseModel):
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    previous_event_name: str = Field(..., alias="previousEventName")
    old_version_id: Optional[str] = Field(None, alias="oldVersionId")
