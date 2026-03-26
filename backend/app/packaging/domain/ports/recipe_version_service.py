from abc import ABC, abstractmethod


class RecipeVersionService(ABC):
    @abstractmethod
    def get_build_arn(self, name: str, version: str) -> str | None: ...

    @abstractmethod
    def create(
        self,
        name: str,
        version: str,
        component_arns: list[str],
        parent_image: str,
        volume_size: int,
        description: str = "",
    ) -> str: ...

    @abstractmethod
    def delete(self, recipe_version_arn: str) -> None: ...
