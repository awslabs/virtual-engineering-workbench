import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineArnValueObject:
    value: str


def from_str(value: str) -> PipelineArnValueObject:
    if not (
        value and re.match(r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image-pipeline/[a-z0-9-_]+$", value)
    ):
        raise domain_exception.DomainException(
            "Pipeline ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image-pipeline/[a-z0-9-_]+$ pattern."
        )

    return PipelineArnValueObject(value=value)
