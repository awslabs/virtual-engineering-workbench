from abc import ABC, abstractmethod

from app.packaging.domain.model.recipe import recipe_version_test_execution


class RecipeVersionTestExecutionQueryService(ABC):
    @abstractmethod
    def get_recipe_version_test_executions(
        self, version_id: str
    ) -> list[recipe_version_test_execution.RecipeVersionTestExecution]: ...

    @abstractmethod
    def get_recipe_version_test_execution(
        self, version_id: str, test_execution_id: str
    ) -> recipe_version_test_execution.RecipeVersionTestExecution | None: ...
