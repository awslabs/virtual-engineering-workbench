from enum import StrEnum

from pydantic import BaseModel, Field


class DynamicParameterType(StrEnum):
    VPC_ID = "VPC_ID"
    BACKEND_SUBNET_IDS = "BACKEND_SUBNET_IDS"
    BACKEND_SUBNET_CIDRS = "BACKEND_SUBNET_CIDRS"


class DynamicParameter(BaseModel):
    name: str = Field(..., title="Name")
    type: DynamicParameterType = Field(..., title="Type")
    tag: str | None = Field(None, title="Tag")  # Format tag_name:tag_value
