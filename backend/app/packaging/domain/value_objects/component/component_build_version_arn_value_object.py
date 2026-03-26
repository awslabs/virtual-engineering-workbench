import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentBuildVersionArnValueObject:
    value: str


def from_str(value: str) -> ComponentBuildVersionArnValueObject:
    if not re.match(
        r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):component/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+/[0-9]+?$",
        value,
    ):
        raise domain_exception.DomainException(
            "Component build version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):component/[a-z0-9-_]+/[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+$ pattern."
        )

    return ComponentBuildVersionArnValueObject(value=value)
