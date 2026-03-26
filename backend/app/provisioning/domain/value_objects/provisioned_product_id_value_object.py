import re
import typing

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model.internal import id_generators
from app.shared.ddd import value_object


class ProvisionedProductIdValueObject(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> ProvisionedProductIdValueObject:
    if not value:
        raise domain_exception.DomainException("Provisioned product ID cannot be empty.")

    return ProvisionedProductIdValueObject(value=value)


def get_new_id(type_prefix: str) -> ProvisionedProductIdValueObject:
    value = id_generators.generate_provisioned_product_id(type_prefix)

    return from_str(value)


def get_new_provisioned_product_id() -> ProvisionedProductIdValueObject:
    return get_new_id("vew-pp")


def from_service_catalog_arn(provisioned_product_arn: typing.Optional[str]):
    """
    Extracts workbench ID from Service Catalog provisioned product ARN.
    Arn example: arn:aws:servicecatalog:us-east-1:001234567890:stack/prod-hpstkrj4ozbem-pa-t3pcfqgq6n262-T0011AA-56838/pp-o7nnwq4nksgli
    """

    if not provisioned_product_arn:
        raise domain_exception.DomainException("Service Catalog provisioned product ARN cannot be empty")

    pp_id_regex = re.compile(r"^arn:aws:servicecatalog:.+:\d+:.+\/(?P<provisioned_product_id>pp-\w+)$")

    pp_id = pp_id_regex.search(provisioned_product_arn).group("provisioned_product_id")

    return ProvisionedProductIdValueObject(value=pp_id)
