from abc import ABC, abstractmethod

from app.packaging.domain.model.component import component_version_test_execution


class ComponentVersionTestExecutionQueryService(ABC):
    @abstractmethod
    def get_component_version_test_executions(
        self, version_id: str
    ) -> list[component_version_test_execution.ComponentVersionTestExecution]: ...

    @abstractmethod
    def get_component_version_test_execution(
        self, version_id: str, test_execution_id: str, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecution | None: ...

    @abstractmethod
    def get_component_version_test_executions_by_test_execution_id(
        self, version_id: str, test_execution_id: str
    ) -> list[component_version_test_execution.ComponentVersionTestExecution]: ...
