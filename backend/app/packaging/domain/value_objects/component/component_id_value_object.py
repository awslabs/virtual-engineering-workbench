import random
import string
import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ComponentIdValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentIdValueObject:
    if not value:
        raise domain_exception.DomainException("Component ID cannot be empty.")

    return ComponentIdValueObject(value=value)


def generate_component_id() -> str:
    return "comp-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))
