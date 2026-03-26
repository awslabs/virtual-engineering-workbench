from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineDescriptionValueObject:
    value: str


def from_str(value: str) -> PipelineDescriptionValueObject:
    if not (value and 1 <= len(value) <= 1024):
        raise domain_exception.DomainException("Pipeline description should be between 1 and 1024 characters.")

    return PipelineDescriptionValueObject(value=value)
