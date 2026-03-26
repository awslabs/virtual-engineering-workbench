import re
import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class RegionValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> RegionValueObject:
    if not value:
        raise domain_exception.DomainException("Region cannot be empty.")

    if not re.match(r"^(us|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\d$", value):
        raise domain_exception.DomainException("Not a valid AWS region.")

    return RegionValueObject(value=value)
