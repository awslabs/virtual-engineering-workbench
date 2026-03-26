from abc import ABC, abstractmethod

from app.packaging.domain.model.component import component_version_test_execution


class ComponentVersionTestingService(ABC):
    @abstractmethod
    def get_testing_environment_image_upstream_id(self, architecture: str, os_version: str, platform: str) -> str: ...

    @abstractmethod
    def get_testing_environment_instance_type(self, architecture: str, os_version: str, platform: str) -> str: ...

    @abstractmethod
    def launch_testing_environment(self, image_upstream_id: str, instance_type: str) -> str: ...

    @abstractmethod
    def get_testing_environment_creation_time(self, instance_id: str) -> str: ...

    @abstractmethod
    def get_testing_environment_status(
        self, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecutionInstanceStatus: ...

    @abstractmethod
    def setup_testing_environment(self, architecture: str, instance_id: str, os_version: str, platform: str) -> str: ...

    @abstractmethod
    def get_testing_command_status(
        self, command_id: str, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecutionCommandStatus: ...

    @abstractmethod
    def run_testing(
        self,
        architecture: str,
        component_version_definition_s3_uri: str,
        instance_id: str,
        os_version: str,
        platform: str,
        component_id: str,
        component_version_id: str,
    ) -> str: ...

    @abstractmethod
    def teardown_testing_environment(self, instance_id: str) -> None: ...

    @abstractmethod
    def get_component_test_bucket_name(self) -> str: ...
