from abc import ABC, abstractmethod


class PipelineService(ABC):
    @abstractmethod
    def create_distribution_config(self, description: str, image_tags: dict[str, str], name: str) -> str: ...

    @abstractmethod
    def create_infrastructure_config(self, description: str, instance_types: list[str], name: str) -> str: ...

    @abstractmethod
    def create_pipeline(
        self,
        description: str,
        distribution_config_arn: str,
        infrastructure_config_arn: str,
        name: str,
        recipe_version_arn: str,
        schedule: str,
    ) -> str: ...

    @abstractmethod
    def delete_distribution_config(self, distribution_config_arn: str) -> None: ...

    @abstractmethod
    def delete_infrastructure_config(self, infrastructure_config_arn: str) -> None: ...

    @abstractmethod
    def delete_pipeline(self, pipeline_arn: str) -> None: ...

    @abstractmethod
    def start_pipeline_execution(self, pipeline_arn: str) -> str: ...

    @abstractmethod
    def update_distribution_config(
        self, description: str, distribution_config_arn: str, image_tags: dict[str, str]
    ) -> str: ...

    @abstractmethod
    def update_infrastructure_config(
        self, description: str, instance_types: list[str], infrastructure_config_arn: str
    ) -> str: ...

    @abstractmethod
    def update_pipeline(
        self,
        description: str,
        distribution_config_arn: str,
        infrastructure_config_arn: str,
        pipeline_arn: str,
        recipe_version_arn: str,
        schedule: str,
    ) -> str: ...

    @abstractmethod
    def get_pipeline_allowed_build_instance_types(self, architecture: str) -> list[str]: ...
