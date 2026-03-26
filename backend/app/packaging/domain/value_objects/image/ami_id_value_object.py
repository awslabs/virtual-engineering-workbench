import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class AmiIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> AmiIdValueObject:
    if not value:
        raise domain_exception.DomainException("Product AMI ID cannot be empty.")

    return AmiIdValueObject(value=value)
