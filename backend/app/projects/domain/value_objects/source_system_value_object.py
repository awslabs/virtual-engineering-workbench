import typing
from enum import Enum

from app.projects.domain.exceptions import domain_exception


class SourceSystemEnum(str, Enum):
    VEW = "VEW"
    RTC = "RTC"

    def __str__(self):
        return str(self.value)


class SourceSystemValueObject:
    def __init__(self, value: SourceSystemEnum) -> None:
        self._value = value

    @property
    def value(self) -> SourceSystemEnum:
        return self._value


def from_str(value: typing.Optional[str]) -> SourceSystemValueObject:
    if not value:
        raise domain_exception.DomainException("Source system cannot be empty.")
    if value.upper().strip() == "VEW":
        return SourceSystemValueObject(SourceSystemEnum.VEW)
    if value.upper().strip() == "RTC":
        return SourceSystemValueObject(SourceSystemEnum.RTC)
    raise domain_exception.DomainException("Unknown source system. Can be 'VEW' or 'RTC'")
