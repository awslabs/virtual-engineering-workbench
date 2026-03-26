from abc import ABC, abstractmethod

from app.packaging.domain.model.recipe import recipe


class RecipeQueryService(ABC):
    @abstractmethod
    def get_recipes(self, project_id: str) -> list[recipe.Recipe]: ...

    @abstractmethod
    def get_recipe(self, project_id: str, recipe_id: str) -> recipe.Recipe | None: ...
