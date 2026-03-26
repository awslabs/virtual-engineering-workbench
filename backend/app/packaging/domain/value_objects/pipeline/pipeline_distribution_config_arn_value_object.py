import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineDistributionConfigArnValueObject:
    value: str


def from_str(value: str) -> PipelineDistributionConfigArnValueObject:
    if not (
        value
        and re.match(
            r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):distribution-configuration/[a-z0-9-_]+$", value
        )
    ):
        raise domain_exception.DomainException(
            "Distribution configuration ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):distribution-configuration/[a-z0-9-_]+$ pattern."
        )

    return PipelineDistributionConfigArnValueObject(value=value)
