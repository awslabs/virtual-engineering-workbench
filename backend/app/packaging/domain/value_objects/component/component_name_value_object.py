import re
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentNameValueObject:
    if not re.match(r"^.{1,100}$", value.strip()):
        raise domain_exception.DomainException("Component name should be between 1 and 100 characters.")

    return ComponentNameValueObject(value=value)
