import random
import string
import typing
from enum import StrEnum

from pydantic import Field

from app.packaging.domain.model.shared import component_version_entry
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_version_id() -> str:
    return "vers-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class RecipeVersionReleaseType(StrEnum):
    Major = "MAJOR"
    Minor = "MINOR"
    Patch = "PATCH"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeVersionReleaseType))


class RecipeVersionStatus(StrEnum):
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
        return list(map(lambda v: v.value, RecipeVersionStatus))


class RecipeVersionPrimaryKey(unit_of_work.PrimaryKey):
    recipeId: str = Field(..., title="RecipeId")
    recipeVersionId: str = Field(..., title="RecipeVersionId")


class RecipeVersion(unit_of_work.Entity):
    recipeId: str = Field(..., title="RecipeId")
    recipeVersionId: str = Field(default_factory=generate_version_id, title="RecipeVersionId")
    parentImageUpstreamId: str = Field(..., title="ParentImageUpstreamId")
    recipeComponentsVersions: list[component_version_entry.ComponentVersionEntry] = Field(
        ..., title="RecipeComponentsVersions"
    )
    recipeVersionIntegrations: list[str] = Field([], title="recipeVersionIntegrations")
    recipeName: str = Field(..., title="RecipeName")
    recipeVersionDescription: str = Field(..., title="RecipeVersionDescription")
    recipeVersionName: str = Field(..., title="RecipeVersionName")
    recipeVersionVolumeSize: str = Field(..., title="RecipeVersionVolumeSize")
    status: RecipeVersionStatus = Field(..., title="Status")
    recipeVersionArn: typing.Optional[str] = Field(None, title="RecipeVersionArn")
    recipeVersionComponentArn: typing.Optional[str] = Field(None, title="RecipeVersionComponentArn")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
