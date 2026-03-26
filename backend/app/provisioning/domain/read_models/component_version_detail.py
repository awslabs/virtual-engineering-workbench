from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentVersionEntryType(StrEnum):
    Main = "MAIN"
    Helper = "HELPER"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionEntryType))


class ComponentVersionDetail(BaseModel):
    componentName: str = Field(..., title="ComponentName")
    componentVersionType: ComponentVersionEntryType = Field(..., title="ComponentVersionType")
    softwareVendor: str = Field(..., title="SoftwareVendor")
    softwareVersion: str = Field(..., title="SoftwareVersion")
    licenseDashboard: str | None = Field(None, title="LicenseDashboard")
    notes: str | None = Field(None, title="Notes")
