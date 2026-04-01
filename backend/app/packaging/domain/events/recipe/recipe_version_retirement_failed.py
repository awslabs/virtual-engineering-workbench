from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionRetirementFailed(message_bus.Message):
    event_name: Literal["RecipeVersionRetirementFailed"] = Field("RecipeVersionRetirementFailed", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    recipe_name: str = Field(..., alias="recipeName")
    recipe_version_name: str = Field(..., alias="recipeVersionName")
    last_updated_by: str = Field(..., alias="lastUpdatedBy")
    model_config = ConfigDict(populate_by_name=True)
