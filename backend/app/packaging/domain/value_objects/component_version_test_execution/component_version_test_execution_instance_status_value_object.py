import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution


@dataclass(frozen=True)
class ComponentVersionTestExecutionInstanceStatusValueObject:
    value: str


def from_str(
    value: typing.Optional[component_version_test_execution.ComponentVersionTestExecutionInstanceStatus],
) -> ComponentVersionTestExecutionInstanceStatusValueObject:
    if not value:
        raise domain_exception.DomainException("Component version test execution instance status cannot be empty.")

    if value not in component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.list():
        raise domain_exception.DomainException(
            "Component version test execution instance status should be in "
            f"{component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.list()}."
        )

    return ComponentVersionTestExecutionInstanceStatusValueObject(value=value)
