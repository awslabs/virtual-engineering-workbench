import re
from dataclasses import dataclass
from typing import List

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeComponentVersionBuildArnValueObjects:
    value: List[str]


def from_list(value: List[str]) -> RecipeComponentVersionBuildArnValueObjects:
    pattern = (
        r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):component/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+/[0-9]+?$"
    )
    for arn in value:
        if not re.match(pattern, arn):
            raise domain_exception.DomainException(f"Component build version ARN should match {pattern} pattern.")
    return RecipeComponentVersionBuildArnValueObjects(value=value)
