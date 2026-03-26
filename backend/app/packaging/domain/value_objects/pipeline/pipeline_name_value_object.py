import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineNameValueObject:
    value: str


def from_str(value: str) -> PipelineNameValueObject:
    if not (value and re.match(r"^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$", value)):
        raise domain_exception.DomainException(
            "Pipeline name should match ^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$ pattern."
        )

    return PipelineNameValueObject(value=value)
