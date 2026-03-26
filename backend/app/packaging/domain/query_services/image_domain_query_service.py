from app.packaging.domain.model.image import image
from app.packaging.domain.ports import image_query_service
from app.packaging.domain.value_objects.image import image_build_version_arn_value_object, image_id_value_object
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_name_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


class ImageDomainQueryService(image_query_service.ImageQueryService):
    def __init__(self, image_qry_srv: image_query_service.ImageQueryService):
        self._image_qry_srv = image_qry_srv

    def get_images(self, project_id: project_id_value_object.ProjectIdValueObject):
        return self._image_qry_srv.get_images(project_id=project_id.value, exclude_status=image.ImageStatus.Deleted)

    def get_images_by_recipe_id_and_version_name(
        self,
        recipe_id: recipe_id_value_object.RecipeIdValueObject,
        recipe_version_name: recipe_version_name_value_object.RecipeVersionNameValueObject,
    ):
        return self._image_qry_srv.get_images_by_recipe_id_and_version_name(
            recipe_id=recipe_id.value, recipe_version_name=recipe_version_name.value
        )

    def get_image(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        image_id: image_id_value_object.ImageIdValueObject,
    ):
        return self._image_qry_srv.get_image(project_id=project_id.value, image_id=image_id.value)

    def get_image_by_image_build_version_arn(
        self, image_build_version_arn: image_build_version_arn_value_object.ImageBuildVersionArnValueObject
    ):
        return self._image_qry_srv.get_image_by_image_build_version_arn(
            image_build_version_arn=image_build_version_arn.value
        )

    def get_image_by_image_upstream_id(self, image_upstream_id: str):
        return self._image_qry_srv.get_image_by_image_upstream_id(image_upstream_id=image_upstream_id)
