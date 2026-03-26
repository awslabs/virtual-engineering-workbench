import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionTestExecutionInstanceIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionTestExecutionInstanceIdValueObject:
    if not re.match(r"^i-[a-z0-9]{17}$", value):
        raise domain_exception.DomainException(
            "Component version test execution instance ID must be a valid instance ID."
        )

    return ComponentVersionTestExecutionInstanceIdValueObject(value=value)
