from abc import ABC, abstractmethod

from app.packaging.domain.model.image import image


class ImageQueryService(ABC):
    @abstractmethod
    def get_images(self, project_id: str, exclude_status: image.ImageStatus | None = None) -> list[image.Image]: ...

    @abstractmethod
    def get_images_by_recipe_id_and_version_name(
        self, recipe_id: str, recipe_version_name: str
    ) -> list[image.Image]: ...

    @abstractmethod
    def get_image(self, project_id: str, image_id: str) -> image.Image | None: ...

    @abstractmethod
    def get_image_by_image_build_version_arn(self, image_build_version_arn: str) -> image.Image | None: ...

    @abstractmethod
    def get_image_by_image_upstream_id(self, image_upstream_id: str) -> image.Image | None: ...
