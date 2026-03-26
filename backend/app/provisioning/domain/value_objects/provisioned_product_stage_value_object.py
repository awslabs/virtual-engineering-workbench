import typing

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioned_product
from app.shared.ddd import value_object


class ProvisionedProductStageValueObject(value_object.ValueObject):
    value: provisioned_product.ProvisionedProductStage


def from_str(value: typing.Optional[str]) -> ProvisionedProductStageValueObject:
    if not value:
        raise domain_exception.DomainException("Stage cannot be empty.")

    enum_value = next(
        (v for v in provisioned_product.ProvisionedProductStage if v.lower().strip() == value.lower().strip()), None
    )

    if not enum_value:
        raise domain_exception.DomainException(f"Stage must be one of {provisioned_product.ProvisionedProductStage}")

    return ProvisionedProductStageValueObject(value=enum_value)
