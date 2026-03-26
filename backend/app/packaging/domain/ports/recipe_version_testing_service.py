from abc import ABC, abstractmethod

from app.packaging.domain.model.recipe import recipe_version_test_execution


class RecipeVersionTestingService(ABC):
    @abstractmethod
    def get_testing_environment_instance_type(self, architecture: str, os_version: str, platform: str) -> str: ...

    @abstractmethod
    def launch_testing_environment(self, image_upstream_id: str, instance_type: str, volume_size: int) -> str: ...

    @abstractmethod
    def get_testing_environment_creation_time(self, instance_id: str) -> str: ...

    @abstractmethod
    def get_testing_environment_status(
        self, instance_id: str
    ) -> recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus: ...

    @abstractmethod
    def setup_testing_environment(self, architecture: str, instance_id: str, os_version: str, platform: str) -> str: ...

    @abstractmethod
    def get_testing_command_status(
        self, command_id: str, instance_id: str
    ) -> recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus: ...

    @abstractmethod
    def run_testing(
        self,
        recipe_version_component_arn: str,
        architecture: str,
        instance_id: str,
        os_version: str,
        platform: str,
        recipe_id: str,
        recipe_version_id: str,
    ) -> str: ...

    @abstractmethod
    def teardown_testing_environment(self, instance_id: str) -> None: ...

    @abstractmethod
    def get_recipe_test_bucket_name(self) -> str: ...
