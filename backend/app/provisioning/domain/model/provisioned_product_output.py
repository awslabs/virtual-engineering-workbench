from typing import Optional

from pydantic import BaseModel, Field


class ProvisionedProductOutput(BaseModel):
    outputKey: str = Field(..., title="OutputKey")
    outputValue: str = Field(..., title="OutputValue")
    description: Optional[str] = Field(None, title="Description")
