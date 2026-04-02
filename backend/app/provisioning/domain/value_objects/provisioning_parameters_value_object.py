import typing

import pydantic

from app.shared.ddd import value_object


class ProvisioningParameter(value_object.ValueObject):
    key: str = pydantic.Field(...)
    value: str = pydantic.Field(...)


class ProvisioningParametersValueObject(value_object.ValueObject):
    value: list[ProvisioningParameter] = pydantic.Field(...)


def from_list(value: typing.Optional[list[dict[str, str]]]) -> ProvisioningParametersValueObject:
    params = [ProvisioningParameter.model_validate(p if isinstance(p, dict) else p.model_dump()) for p in (value or [])]
    return ProvisioningParametersValueObject(value=params)
