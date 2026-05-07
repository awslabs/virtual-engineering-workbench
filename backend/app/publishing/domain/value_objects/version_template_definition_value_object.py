import re
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception

_JINJA2_CONTROL_PATTERN = re.compile(r"\{\{|\{%|\{#")


@dataclass(frozen=True)
class VersionTemplateDefinitionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> VersionTemplateDefinitionValueObject:
    if not value:
        raise domain_exception.DomainException("Version template definition cannot be empty.")

    return VersionTemplateDefinitionValueObject(value=value)
