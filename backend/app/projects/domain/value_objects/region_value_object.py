import re
import typing

from app.projects.domain.exceptions import domain_exception


class RegionValueObject:
    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value


def from_str(value: typing.Optional[str]) -> RegionValueObject:
    if not value:
        raise domain_exception.DomainException("Region cannot be empty.")

    if not re.match(r"^(us|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\d$", value):
        raise domain_exception.DomainException("Not a valid AWS region.")

    return RegionValueObject(value)
