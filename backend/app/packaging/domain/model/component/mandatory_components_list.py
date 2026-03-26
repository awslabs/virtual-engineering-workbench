from pydantic import Field

from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class MandatoryComponentsListPrimaryKey(unit_of_work.PrimaryKey):
    mandatoryComponentsListPlatform: str = Field(..., title="MandatoryComponentsListPlatform")
    mandatoryComponentsListOsVersion: str = Field(..., title="MandatoryComponentsListOsVersion")
    mandatoryComponentsListArchitecture: str = Field(..., title="MandatoryComponentsListArchitecture")


class MandatoryComponentsList(unit_of_work.Entity):
    mandatoryComponentsListPlatform: str = Field(..., title="MandatoryComponentsListPlatform")
    mandatoryComponentsListOsVersion: str = Field(..., title="MandatoryComponentsListOsVersion")
    mandatoryComponentsListArchitecture: str = Field(..., title="MandatoryComponentsListArchitecture")
    mandatoryComponentsVersions: list[ComponentVersionEntry] = Field(..., title="MandatoryComponentsVersions")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
