from pydantic import BaseModel, Field


class ComponentVersionEntryType(str):
    Main = "MAIN"
    Helper = "HELPER"


class ComponentVersionDetail(BaseModel):
    component_name: str = Field(..., alias="componentName")
    component_version_type: str = Field(..., alias="componentVersionType")
    software_vendor: str = Field(..., alias="softwareVendor")
    software_version: str = Field(..., alias="softwareVersion")
    license_dashboard: str | None = Field(None, alias="licenseDashboard")
    notes: str | None = Field(None, alias="notes")


class AutomatedImageRegistrationCompleted(BaseModel):
    event_name: str = Field("AutomatedImageRegistrationCompleted", alias="eventName", const=True)
    ami_id: str = Field(..., alias="amiId")
    product_id: str = Field(..., alias="productId")
    project_id: str = Field(..., alias="projectId")
    release_type: str = Field(..., alias="releaseType")
    user_id: str = Field(..., alias="userId")
    components_versions_details: list[ComponentVersionDetail] = Field(..., alias="componentsVersionsDetails")
    os_version: str = Field(..., alias="osVersion")
    platform: str = Field(..., alias="platform")
    architecture: str = Field(..., alias="architecture")
    integrations: list[str] = Field([], title="integrations")
