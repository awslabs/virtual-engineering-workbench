from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionPublished(message_bus.Message):
    event_name: str = Field("RecipeVersionPublished", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")

    class Config:
        allow_population_by_field_name = True
