import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution


@dataclass(frozen=True)
class ComponentVersionTestExecutionCommandStatusValueObject:
    value: str


def from_str(
    value: typing.Optional[component_version_test_execution.ComponentVersionTestExecutionCommandStatus],
) -> ComponentVersionTestExecutionCommandStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Command status cannot be empty.")

    if value not in component_version_test_execution.ComponentVersionTestExecutionCommandStatus.list():
        raise domain_exception.DomainException(
            f"Command status should be in {component_version_test_execution.ComponentVersionTestExecutionCommandStatus.list()}."
        )

    return ComponentVersionTestExecutionCommandStatusValueObject(value=value)
