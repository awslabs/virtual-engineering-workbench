import typing

import pydantic

from app.provisioning.domain.model import additional_configuration
from app.shared.ddd import value_object


class AdditionalConfigurationsValueObject(value_object.ValueObject):
    value: list[additional_configuration.AdditionalConfiguration] = pydantic.Field(...)


def from_list(value: typing.Optional[list[dict[str, list[dict[str, str]]]]]) -> AdditionalConfigurationsValueObject:
    return AdditionalConfigurationsValueObject(
        value=[additional_configuration.AdditionalConfiguration.parse_obj(c) for c in (value or [])]
    )
