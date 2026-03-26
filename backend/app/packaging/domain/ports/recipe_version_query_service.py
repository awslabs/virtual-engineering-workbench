from abc import ABC, abstractmethod

from app.packaging.domain.model.recipe import recipe_version, recipe_version_summary


class RecipeVersionQueryService(ABC):
    @abstractmethod
    def get_latest_recipe_version_name(self, recipe_id: str) -> str | None: ...

    @abstractmethod
    def get_recipe_versions(self, recipe_id: str) -> list[recipe_version.RecipeVersion]: ...

    @abstractmethod
    def get_recipe_version(self, recipe_id: str, version_id: str) -> recipe_version.RecipeVersion | None: ...

    @abstractmethod
    def get_all_recipe_versions(self, status: str) -> list[recipe_version_summary.RecipeVersionSummary]: ...
