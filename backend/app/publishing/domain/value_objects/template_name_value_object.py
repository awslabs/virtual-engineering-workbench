import os
import typing
from dataclasses import dataclass

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class TemplateNameValueObject:
    value: str

    def get_filename(self) -> str:
        return os.path.basename(self.value)


TEMPLATE_SUFFIXES = [".yml", ".yaml", ".json"]


def from_str(value: typing.Optional[str]) -> TemplateNameValueObject:
    if not value:
        raise domain_exception.DomainException("Template Name cannot be empty.")

    if not next((suffix for suffix in TEMPLATE_SUFFIXES if value.endswith(suffix)), None):
        raise domain_exception.DomainException(f"Template suffix must be one of {TEMPLATE_SUFFIXES}")

    return TemplateNameValueObject(value=value)
