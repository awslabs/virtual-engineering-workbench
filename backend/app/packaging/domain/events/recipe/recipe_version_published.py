from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionPublished(message_bus.Message):
    event_name: Literal["RecipeVersionPublished"] = Field("RecipeVersionPublished", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    model_config = ConfigDict(populate_by_name=True)
