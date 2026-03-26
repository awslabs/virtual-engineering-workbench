import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentVersionTestExecutionImageUpstreamIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionTestExecutionImageUpstreamIdValueObject:
    if not re.match(r"^ami-[a-z0-9]{17}$", value):
        raise domain_exception.DomainException(
            "Component version test execution image upstream ID must be a valid image ID."
        )

    return ComponentVersionTestExecutionImageUpstreamIdValueObject(value=value)
