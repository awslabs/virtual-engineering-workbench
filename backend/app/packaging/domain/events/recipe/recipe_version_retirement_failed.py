from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionRetirementFailed(message_bus.Message):
    event_name: str = Field("RecipeVersionRetirementFailed", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    recipe_name: str = Field(..., alias="recipeName")
    recipe_version_name: str = Field(..., alias="recipeVersionName")
    last_updated_by: str = Field(..., alias="lastUpdatedBy")

    class Config:
        allow_population_by_field_name = True
