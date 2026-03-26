import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class StageValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> StageValueObject:
    if not value:
        raise domain_exception.DomainException("Stage cannot be empty.")

    value = value.upper()
    if value not in ["DEV", "QA", "PROD"]:
        raise domain_exception.DomainException("Not a valid Stage. Should be dev, qa or prod")

    return StageValueObject(value=value)
