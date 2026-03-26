from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioned_product
from app.shared.ddd import value_object


class DeploymentOptionValueObject(value_object.ValueObject):
    value: provisioned_product.DeploymentOption


def from_str(value: str | None) -> DeploymentOptionValueObject:
    # Default to MULTI_AZ if None for backward compatibility
    if value is None:
        return DeploymentOptionValueObject(value=provisioned_product.DeploymentOption.MULTI_AZ)

    if not value:
        raise domain_exception.DomainException("Deployment option cannot be empty.")

    if value.upper() not in provisioned_product.DeploymentOption.list():
        raise domain_exception.DomainException(
            f"Not a valid deployment option. Should be in {provisioned_product.DeploymentOption.list()}"
        )

    return DeploymentOptionValueObject(value=provisioned_product.DeploymentOption(value.upper()))


def multi_az() -> DeploymentOptionValueObject:
    return DeploymentOptionValueObject(value=provisioned_product.DeploymentOption.MULTI_AZ)
