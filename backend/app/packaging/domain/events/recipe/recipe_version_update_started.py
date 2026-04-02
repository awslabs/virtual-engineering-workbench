from typing import Literal

from pydantic import ConfigDict, Field

from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.shared.adapters.message_bus import message_bus


class RecipeVersionUpdateStarted(message_bus.Message):
    event_name: Literal["RecipeVersionUpdateStarted"] = Field("RecipeVersionUpdateStarted", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    parent_image_upstream_id: str = Field(..., alias="parentImageUpstreamId")
    previous_recipe_components_versions: list[ComponentVersionEntry] = Field(
        list(), alias="previousRecipeComponentsVersions"
    )
    recipe_components_versions: list[ComponentVersionEntry] = Field(..., alias="recipeComponentsVersions")
    recipe_version_name: str = Field(..., alias="recipeVersionName")
    recipe_version_volume_size: str = Field(..., alias="recipeVersionVolumeSize")
    model_config = ConfigDict(populate_by_name=True)
