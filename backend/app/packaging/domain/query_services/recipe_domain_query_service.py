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
