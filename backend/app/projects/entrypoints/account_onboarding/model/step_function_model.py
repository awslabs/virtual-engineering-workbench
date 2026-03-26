from typing import Optional

from pydantic import BaseModel, Field


class SetupDynamicResourcesRequest(BaseModel):
    event_type: str = Field("SetupDynamicResourcesRequest", alias="eventType")
    account_id: str = Field(..., alias="accountId")
    region: str = Field(..., alias="region")


class SetupDynamicResourcesResponse(BaseModel):
    event_type: str = Field("SetupDynamicResourcesResponse", alias="eventType")


class SetupPrerequisitesResourcesRequest(BaseModel):
    event_type: str = Field("SetupPrerequisitesResourcesRequest", alias="eventType")
    account_id: str = Field(..., alias="accountId")
    region: str = Field(..., alias="region")
    variables: Optional[dict[str, str]] = Field(None, alias="variables")


class SetupPrerequisitesResourcesResponse(BaseModel):
    event_type: str = Field("SetupPrerequisitesResourcesResponse", alias="eventType")


class SetupStaticResourcesRequest(BaseModel):
    event_type: str = Field("SetupStaticResourcesRequest", alias="eventType")
    account_id: str = Field(..., alias="accountId")
    region: str = Field(..., alias="region")
    variables: Optional[dict[str, str]] = Field(None, alias="variables")


class SetupStaticResourcesResponse(BaseModel):
    event_type: str = Field("SetupStaticResourcesResponse", alias="eventType")


class CompleteProjectAccountOnboardingRequest(BaseModel):
    event_type: str = Field("CompleteProjectAccountOnboardingRequest", alias="eventType")
    project_id: str = Field(..., alias="projectId")
    project_account_id: str = Field(..., alias="projectAccountId")


class CompleteProjectAccountOnboardingResponse(BaseModel):
    event_type: str = Field("CompleteProjectAccountOnboardingResponse", alias="eventType")


class FailProjectAccountOnboardingRequest(BaseModel):
    event_type: str = Field("FailProjectAccountOnboardingRequest", alias="eventType")
    project_id: str = Field(..., alias="projectId")
    project_account_id: str = Field(..., alias="projectAccountId")
    error: str = Field(None, alias="error")
    cause: str = Field(None, alias="cause")


class FailProjectAccountOnboardingResponse(BaseModel):
    event_type: str = Field("FailProjectAccountOnboardingResponse", alias="eventType")
