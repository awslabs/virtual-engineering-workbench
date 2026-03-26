import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution


@dataclass(frozen=True)
class RecipeVersionTestExecutionInstanceStatusValueObject:
    value: str


def from_str(
    value: typing.Optional[recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus],
) -> RecipeVersionTestExecutionInstanceStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version test execution instance status cannot be empty.")

    if value not in recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.list():
        raise domain_exception.DomainException(
            "Recipe version test execution instance status should be in "
            f"{recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.list()}."
        )

    return RecipeVersionTestExecutionInstanceStatusValueObject(value=value)
