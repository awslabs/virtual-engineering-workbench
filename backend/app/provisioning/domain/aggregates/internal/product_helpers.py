from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioning_parameter
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import provisioning_parameters_value_object

TECHNICAL_PARAMETER_TYPE_PREFIX = "AWS::"


def validate_provisioning_parameters(
    requested_provisioning_parameters: list[provisioning_parameters_value_object.ProvisioningParameter],
    product_provisioning_parameters: list[version.VersionParameter],
):
    technical_parameters = []
    user_parameters = []

    # TODO: We can get rid of the manual check and instead use isTechnicalParameter attribute once
    # new versions are propogated with this attribute.
    if product_provisioning_parameters:
        technical_parameters = {
            wb.parameterKey
            for wb in product_provisioning_parameters
            if wb.parameterType and wb.parameterType.startswith(TECHNICAL_PARAMETER_TYPE_PREFIX)
        }

        user_parameters = {
            wb.parameterKey
            for wb in product_provisioning_parameters
            if not wb.parameterType or not wb.parameterType.startswith(TECHNICAL_PARAMETER_TYPE_PREFIX)
        }

    requested_technical_parameters = [p.key for p in requested_provisioning_parameters if p.key in technical_parameters]

    if requested_technical_parameters:
        raise domain_exception.DomainException(
            f"Technical parameters {', '.join(requested_technical_parameters)} cannot be overridden."
        )

    requested_invalid_parameters = [p.key for p in requested_provisioning_parameters if p.key not in user_parameters]

    if requested_invalid_parameters:
        raise domain_exception.DomainException(
            f"Product does not accept these parameters: {', '.join(requested_invalid_parameters)}."
        )


def map_provisioning_parameters(
    requested_provisioning_parameters: list[provisioning_parameters_value_object.ProvisioningParameter],
    product_provisioning_parameters: list[version.VersionParameter],
    current_provisioned_parameters: list[provisioning_parameters_value_object.ProvisioningParameter] | None = None,
) -> list[provisioning_parameter.ProvisioningParameter]:
    # Map all parameters
    params = [
        provisioning_parameter.ProvisioningParameter(
            key=p.parameterKey,
            value=p.defaultValue,
            isTechnicalParameter=p.isTechnicalParameter,
            parameterType=p.parameterType,
        )
        for p in product_provisioning_parameters
    ]
    # Update default parameters if the parameter already exists and is in allowed parameter values
    for current_param in current_provisioned_parameters:
        for param in params:
            version_parameter = next(
                (v_param for v_param in product_provisioning_parameters if v_param.parameterKey == param.key), None
            )
            if not version_parameter.parameterConstraints or not version_parameter.parameterConstraints.allowedValues:
                continue
            if (
                param.key == current_param.key
                and current_param.value in version_parameter.parameterConstraints.allowedValues
            ):
                param.value = current_param.value

    # Update values of parameters supplied by the user
    for requested_param in requested_provisioning_parameters:
        param = next((param for param in params if param.key == requested_param.key), None)
        if param:
            param.value = requested_param.value

    # The VpcIdSSM provisioning parameter is a technical parameter defined only in CloudFormation Template.
    # Until VpcIdSSM parameter is not migrated domain logic needs to ensure that initial VPC ID is used for provisioning
    # TODO: Remove manual parameter attribute update after new VpcId parameter is added to product_provisioning_parameters
    vpc_id_param = next(filter(lambda param: param.key == "VpcIdSSM", params), None)
    if vpc_id_param:
        vpc_id_param.usePreviousValue = True

    return params
