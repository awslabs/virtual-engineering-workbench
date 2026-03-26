from enum import StrEnum

from pydantic import BaseModel, Field


class ProvisionedProductConfigurationTypeEnum(StrEnum):
    VVPLProvisionedProductConfiguration = "VVPL_PROVISIONED_PRODUCT_CONFIGURATION"


class AdditionalConfigurationRunStatus(StrEnum):
    InProgress = "IN_PROGRESS"
    Success = "SUCCESS"
    Failed = "FAILED"


class AdditionalConfigurationParameter(BaseModel):
    key: str = Field(..., title="Key")
    value: str = Field(..., title="Value")


class AdditionalConfiguration(BaseModel):
    type: ProvisionedProductConfigurationTypeEnum = Field(..., title="Type")
    parameters: list[AdditionalConfigurationParameter] = Field(..., title="Parameters")
    run_id: str | None = Field(None, title="RunId")
