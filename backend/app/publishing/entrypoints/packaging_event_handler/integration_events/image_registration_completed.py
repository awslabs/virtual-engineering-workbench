from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentVersionEntryType(StrEnum):
    Main = "MAIN"
    Helper = "HELPER"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionEntryType))


class ComponentVersionDetail(BaseModel):
    component_name: str = Field(..., alias="componentName")
    component_version_type: ComponentVersionEntryType = Field(..., alias="componentVersionType")
    software_vendor: str = Field(..., alias="softwareVendor")
    software_version: str = Field(..., alias="softwareVersion")
    license_dashboard: str | None = Field(None, alias="licenseDashboard")
    notes: str | None = Field(None, alias="notes")


class ImageRegistrationCompleted(BaseModel):
    event_name: str = Field("ImageRegistrationCompleted", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    ami_description: str = Field(..., alias="amiDescription")
    ami_id: str = Field(..., alias="amiId")
    ami_name: str = Field(..., alias="amiName")
    components_versions_details: list[ComponentVersionDetail] = Field(..., alias="componentsVersionsDetails")
    retired_ami_ids: list[str] = Field(..., alias="retiredAmiIds")
    os_version: str = Field(..., alias="osVersion")
    platform: str = Field(..., alias="platform")
    architecture: str = Field(..., alias="architecture")
    integrations: list[str] = Field([], title="integrations")
    create_date: str = Field(..., alias="createDate")
