from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineIdValueObject:
    value: str


def from_str(value: str) -> PipelineIdValueObject:
    if not value:
        raise domain_exception.DomainException("Pipeline ID cannot be empty.")

    return PipelineIdValueObject(value=value)
