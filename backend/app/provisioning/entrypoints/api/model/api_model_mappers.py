from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.model import provisioned_product, workbench_failure
from app.provisioning.entrypoints.api.model import api_model

SENSITIVE_OUTPUT_PARAMETERS = {
    product_provisioning_aggregate.PRODUCT_OUTPUT_SSH_KEY_NAME,
    product_provisioning_aggregate.PRODUCT_OUTPUT_SSH_KEY_ID,
    product_provisioning_aggregate.PRODUCT_OUTPUT_USER_CREDENTIALS_NAME,
}


def map_provisioned_product(
    provisioned_product_entity: provisioned_product.ProvisionedProduct,
    include_sensitive: bool = False,
) -> api_model.ProvisionedProduct:
    provisioned_product_response = (
        api_model.ProvisionedProductInternal.model_validate(provisioned_product_entity.model_dump())
        if include_sensitive
        else api_model.ProvisionedProduct.model_validate(provisioned_product_entity.model_dump())
    )
    provisioned_product_response.sshEnabled = provisioned_product_entity.sshKeyPath is not None
    provisioned_product_response.usernamePasswordLoginEnabled = (
        provisioned_product_entity.userCredentialName is not None
    )
    provisioned_product_response.outputs = [
        output
        for output in provisioned_product_response.outputs or []
        if output.outputKey not in SENSITIVE_OUTPUT_PARAMETERS
    ]
    failure = workbench_failure.describe_failure(
        status=provisioned_product_entity.status,
        status_reason=provisioned_product_entity.statusReason,
        failed_operation=provisioned_product_entity.failedOperation,
        instance_type=_instance_type(provisioned_product_entity),
    )
    provisioned_product_response.failure = (
        api_model.WorkbenchFailure.model_validate(failure.model_dump()) if failure else None
    )
    return provisioned_product_response


def _instance_type(provisioned_product_entity: provisioned_product.ProvisionedProduct) -> str | None:
    return next(
        (
            parameter.value
            for parameter in provisioned_product_entity.provisioningParameters or []
            if parameter.key == "InstanceType"
        ),
        None,
    )
