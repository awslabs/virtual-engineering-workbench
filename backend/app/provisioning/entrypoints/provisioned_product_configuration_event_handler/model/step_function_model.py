from pydantic import BaseModel, Field

from app.provisioning.domain.model import additional_configuration


class StartProvisionedProductConfigurationRequest(BaseModel):
    event_type: str = Field("StartProvisionedProductConfigurationRequest", alias="eventType")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")


class StartProvisionedProductConfigurationResponse(BaseModel):
    event_type: str = Field("StartProvisionedProductConfigurationResponse", alias="eventType")


class GetProvisionedProductConfigurationStatusRequest(BaseModel):
    event_type: str = Field("GetProvisionedProductConfigurationStatusRequest", alias="eventType")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")


class GetProvisionedProductConfigurationStatusResponse(BaseModel):
    event_type: str = Field("GetProvisionedProductConfigurationStatusResponse", alias="eventType")
    status: additional_configuration.AdditionalConfigurationRunStatus = Field(
        ..., alias="status", description="SUCCESS/FAILED/IN_PROGRESS"
    )
    reason: str = Field(..., alias="reason")


class FailProvisionedProductConfigurationRequest(BaseModel):
    event_type: str = Field("FailProvisionedProductConfigurationRequest", alias="eventType")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    reason: str = Field(..., alias="reason")


class FailProvisionedProductConfigurationResponse(BaseModel):
    event_type: str = Field("FailProvisionedProductConfigurationResponse", alias="eventType")


class CompleteProvisionedProductConfigurationRequest(BaseModel):
    event_type: str = Field("CompleteProvisionedProductConfigurationRequest", alias="eventType")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")


class CompleteProvisionedProductConfigurationResponse(BaseModel):
    event_type: str = Field("CompleteProvisionedProductConfigurationResponse", alias="eventType")


class IsProvisionedProductReadyRequest(BaseModel):
    event_type: str = Field("IsProvisionedProductReadyRequest", alias="eventType")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")


class IsProvisionedProductReadyResponse(BaseModel):
    event_type: str = Field("IsProvisionedProductReadyResponse", alias="eventType")
    is_ready: bool = Field(..., alias="isReady")
