import random
import string
from enum import StrEnum

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_recipe_id() -> str:
    return "reci-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class RecipePlatform(StrEnum):
    Linux = "Linux"
    Windows = "Windows"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipePlatform))


class RecipeArchitecture(StrEnum):
    Amd64 = "amd64"
    Arm64 = "arm64"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeArchitecture))


class RecipeOsVersion(StrEnum):
    Ubuntu_24 = "Ubuntu 24"
    Windows_2025 = "Microsoft Windows Server 2025"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeOsVersion))


class RecipePrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    recipeId: str = Field(..., title="RecipeId")


class RecipeStatus(StrEnum):
    Archived = "ARCHIVED"
    Created = "CREATED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeStatus))


class Recipe(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    recipeId: str = Field(default_factory=generate_recipe_id, title="RecipeId")
    recipeName: str = Field(..., title="RecipeName")
    recipeDescription: str = Field(..., title="RecipeDescription")
    recipePlatform: str = Field(..., title="RecipePlatform")
    recipeArchitecture: str = Field(..., title="RecipeArchitecture")
    recipeOsVersion: str = Field(..., title="RecipeOsVersion")
    status: RecipeStatus = Field(..., title="Status")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
