import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineInfrastructureConfigArnValueObject:
    value: str


def from_str(value: str) -> PipelineInfrastructureConfigArnValueObject:
    if not (
        value
        and re.match(
            r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):infrastructure-configuration/[a-z0-9-_]+$", value
        )
    ):
        raise domain_exception.DomainException(
            "Infrastructure configuration ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):infrastructure-configuration/[a-z0-9-_]+$ pattern."
        )

    return PipelineInfrastructureConfigArnValueObject(value=value)
