from typing import Optional

from pydantic import BaseModel, Field


class ProvisioningParameter(BaseModel):
    key: str = Field(..., title="Key")
    value: Optional[str] = Field(None, title="Value")
    isTechnicalParameter: bool = Field(False, title="IsTechnicalParameter")
    parameterType: Optional[str] = Field(None, title="ParameterType")
    usePreviousValue: Optional[bool] = Field(False, title="UsePreviousValue")
