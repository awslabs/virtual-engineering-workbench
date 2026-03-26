import random
import string
from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.packaging.domain.model.shared.recipe_version_entry import RecipeVersionEntry
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_version_id() -> str:
    return "vers-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class ComponentVersionReleaseType(StrEnum):
    Major = "MAJOR"
    Minor = "MINOR"
    Patch = "PATCH"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionReleaseType))


class ComponentVersionStatus(StrEnum):
    Creating = "CREATING"
    Created = "CREATED"
    Failed = "FAILED"
    Released = "RELEASED"
    Testing = "TESTING"
    Updating = "UPDATING"
    Validated = "VALIDATED"
    Retired = "RETIRED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionStatus))


class ComponentVersionPrimaryKey(unit_of_work.PrimaryKey):
    componentId: str = Field(..., title="ComponentId")
    componentVersionId: str = Field(..., title="ComponentVersionId")


class ComponentVersion(unit_of_work.Entity):
    componentId: str = Field(..., title="ComponentId")
    componentVersionId: str = Field(default_factory=generate_version_id, title="ComponentVersionId")
    componentName: str = Field(..., title="ComponentName")
    componentVersionName: str = Field(..., title="ComponentVersionName")
    componentVersionDescription: str = Field(..., title="ComponentVersionDescription")
    componentBuildVersionArn: Optional[str] = Field(None, title="ComponentBuildVersionArn")
    componentVersionS3Uri: Optional[str] = Field(None, title="ComponentVersionS3Uri")
    componentPlatform: str = Field(..., title="ComponentPlatform")
    componentSupportedArchitectures: list[str] = Field(..., title="ComponentSupportedArchitectures")
    componentSupportedOsVersions: list[str] = Field(..., title="ComponentSupportedOsVersions")
    associatedComponentsVersions: Optional[list[ComponentVersionEntry]] = Field(
        None, title="AssociatedComponentsVersions"
    )
    associatedRecipesVersions: Optional[list[RecipeVersionEntry]] = Field(None, title="AssociatedRecipesVersions")
    componentVersionDependencies: Optional[list[ComponentVersionEntry]] = Field(
        None, title="ComponentVersionDependencies"
    )
    softwareVendor: str = Field(..., title="SoftwareVendor")
    softwareVersion: str = Field(..., title="SoftwareVersion")
    licenseDashboard: Optional[str] = Field(None, title="LicenseDashboard")
    notes: Optional[str] = Field(None, title="Notes")
    status: ComponentVersionStatus = Field(..., title="Status")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
