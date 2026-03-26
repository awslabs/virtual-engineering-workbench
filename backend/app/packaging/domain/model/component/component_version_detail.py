from typing import Optional

from pydantic import BaseModel, Field

from app.packaging.domain.model.shared import component_version_entry


class ComponentVersionDetail(BaseModel):
    componentName: str = Field(..., title="ComponentName")
    componentVersionType: component_version_entry.ComponentVersionEntryType = Field(..., title="ComponentVersionType")
    softwareVendor: str = Field(..., title="SoftwareVendor")
    softwareVersion: str = Field(..., title="SoftwareVersion")
    licenseDashboard: Optional[str] = Field(None, title="LicenseDashboard")
    notes: Optional[str] = Field(None, title="Notes")
