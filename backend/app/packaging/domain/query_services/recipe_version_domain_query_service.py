from app.packaging.domain.ports import recipe_query_service, recipe_version_query_service
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_id_value_object,
    recipe_version_status_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object


class RecipeVersionDomainQueryService:
    def __init__(
        self,
        recipe_qry_srv: recipe_query_service.RecipeQueryService,
        recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    ):
        self._recipe_qry_srv = recipe_qry_srv
        self._recipe_version_qry_srv = recipe_version_qry_srv

    def get_latest_recipe_version_name(self, recipe_id: recipe_id_value_object.RecipeIdValueObject):
        return self._recipe_version_qry_srv.get_latest_recipe_version_name(recipe_id=recipe_id.value)

    def get_recipe_versions(self, recipe_id: recipe_id_value_object.RecipeIdValueObject):
        return self._recipe_version_qry_srv.get_recipe_versions(recipe_id=recipe_id.value)

    def get_recipe_version(
        self,
        recipe_id: recipe_id_value_object.RecipeIdValueObject,
        version_id: recipe_version_id_value_object.RecipeVersionIdValueObject,
    ):
        return self._recipe_version_qry_srv.get_recipe_version(recipe_id=recipe_id.value, version_id=version_id.value)

    def get_all_recipes_versions(
        self,
        status: recipe_version_status_value_object.RecipeVersionStatusValueObject,
        project_id: project_id_value_object.ProjectIdValueObject = None,
    ):
        recipe_versions = self._recipe_version_qry_srv.get_all_recipe_versions(
            status=status.value,
        )
        if project_id:
            project_recipes = self._recipe_qry_srv.get_recipes(project_id=project_id.value)
            project_recipe_ids = [recipe.recipeId for recipe in project_recipes]
            recipe_versions = [
                recipe_version for recipe_version in recipe_versions if recipe_version.recipeId in project_recipe_ids
            ]

        return recipe_versions
