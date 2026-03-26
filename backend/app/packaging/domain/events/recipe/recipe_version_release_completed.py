from pydantic import Field

from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.shared.adapters.message_bus import message_bus


class RecipeVersionReleaseCompleted(message_bus.Message):
    event_name: str = Field("RecipeVersionReleaseCompleted", alias="eventName", const=True)
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    recipe_component_versions: list[ComponentVersionEntry] = Field(..., alias="recipeComponentsVersions")

    class Config:
        allow_population_by_field_name = True
