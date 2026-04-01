from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.model import provisioned_product
from app.provisioning.entrypoints.s2s_api.model import api_model

SENSITIVE_OUTPUT_PARAMETERS = {
    product_provisioning_aggregate.PRODUCT_OUTPUT_SSH_KEY_NAME,
    product_provisioning_aggregate.PRODUCT_OUTPUT_USER_CREDENTIALS_NAME,
}


def map_provisioned_product(
    provisioned_product_entity: provisioned_product.ProvisionedProduct,
) -> api_model.ProvisionedProduct:
    provisioned_product_response = api_model.ProvisionedProduct.model_validate(provisioned_product_entity.model_dump())
    provisioned_product_response.sshEnabled = provisioned_product_entity.sshKeyPath is not None
    provisioned_product_response.usernamePasswordLoginEnabled = (
        provisioned_product_entity.userCredentialName is not None
    )
    provisioned_product_response.outputs = [
        output
        for output in provisioned_product_response.outputs or []
        if output.outputKey not in SENSITIVE_OUTPUT_PARAMETERS
    ]
    return provisioned_product_response
