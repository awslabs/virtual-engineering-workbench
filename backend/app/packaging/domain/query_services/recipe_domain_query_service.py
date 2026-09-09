from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.ports import recipe_query_service
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


class RecipeDomainQueryService:
    def __init__(self, recipe_qry_srv: recipe_query_service.RecipeQueryService):
        self._recipe_qry_srv = recipe_qry_srv

    def get_recipes(self, project_id: project_id_value_object.ProjectIdValueObject):
        return self._recipe_qry_srv.get_recipes(project_id=project_id.value)

    def get_recipe(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        recipe_id: recipe_id_value_object.RecipeIdValueObject,
    ):
        return self._recipe_qry_srv.get_recipe(project_id=project_id.value, recipe_id=recipe_id.value)

    def require_recipe_in_project(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        recipe_id: recipe_id_value_object.RecipeIdValueObject,
    ) -> None:
        """Raise when the recipe does not belong to the given project.

        A recipe is stored under its project, so a recipe the project does not hold is not readable
        through that project's routes.
        """

        if self._recipe_qry_srv.get_recipe(project_id=project_id.value, recipe_id=recipe_id.value) is None:
            raise NotFoundError(f"Recipe {recipe_id.value} not found in project {project_id.value}.")
