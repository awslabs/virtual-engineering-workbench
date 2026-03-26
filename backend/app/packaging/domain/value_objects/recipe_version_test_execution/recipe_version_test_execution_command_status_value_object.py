import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution


@dataclass(frozen=True)
class RecipeVersionTestExecutionCommandStatusValueObject:
    value: str


def from_str(
    value: typing.Optional[recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus],
) -> RecipeVersionTestExecutionCommandStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Command status cannot be empty.")

    if value not in recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.list():
        raise domain_exception.DomainException(
            f"Command status should be in {recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.list()}."
        )

    return RecipeVersionTestExecutionCommandStatusValueObject(value=value)
