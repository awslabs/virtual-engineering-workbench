import re
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RegionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RegionValueObject:
    if not value:
        raise domain_exception.DomainException("Region cannot be empty.")

    if not re.match(r"^(us|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\d$", value):
        raise domain_exception.DomainException("Not a valid AWS region.")

    return RegionValueObject(value=value)
