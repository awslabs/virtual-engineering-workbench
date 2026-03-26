from abc import ABC, abstractmethod


class RecipeComponentVersionDefinitionService(ABC):
    @abstractmethod
    def upload_recipe(
        self, recipe_id: str, pre_release: bool, recipe_component_version_name: str, component_definition: bytes
    ) -> str: ...
