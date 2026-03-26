import enum

from infra import constants
from infra.auth import shared_auth_schema


class ProvisioningBCActions(enum.StrEnum):
    AuthorizeUserIpAddress = "AuthorizeUserIpAddress"
    GetAvailableProducts = "GetAvailableProducts"
    GetAvailableProductVersions = "GetAvailableProductVersions"
    GetFeatures = "GetFeatures"
    GetProjectPaginatedProvisionedProducts = "GetProjectPaginatedProvisionedProducts"
    GetProjectProvisionedProducts = "GetProjectProvisionedProducts"
    GetProductsIPMappings = "GetProductsIPMappings"
    GetProvisionedProduct = "GetProvisionedProduct"
    GetProvisionedProductActivities = "GetProvisionedProductActivities"
    GetProvisionedProducts = "GetProvisionedProducts"
    GetProvisionedProductSSHKey = "GetProvisionedProductSSHKey"
    GetProvisionedProductUserCredentials = "GetProvisionedProductUserCredentials"
    GetSwaggerSpec = "GetSwaggerSpec"
    GetUserProfile = "GetUserProfile"
    GetUsersWithinMaintenanceWindow = "GetUsersWithinMaintenanceWindow"
    InternalGetProvisionedProduct = "InternalGetProvisionedProduct"
    InternalGetProvisioningSubnets = "InternalGetProvisioningSubnets"
    LaunchProduct = "LaunchProduct"
    RemoveProvisionedProduct = "RemoveProvisionedProduct"
    RemoveProvisionedProducts = "RemoveProvisionedProducts"
    StartProvisionedProduct = "StartProvisionedProduct"
    StopProvisionedProduct = "StopProvisionedProduct"
    StopProvisionedProducts = "StopProvisionedProducts"
    UpdateFeatures = "UpdateFeatures"
    UpdateProvisionedProduct = "UpdateProvisionedProduct"
    UpdateProductsIPMappings = "UpdateProductsIPMappings"
    UpdateUserProfile = "UpdateUserProfile"


provisioning_bc_actions = {
    action.value: {
        "appliesTo": {
            "resourceTypes": [
                shared_auth_schema.SharedEntities.Project,
            ],
            "principalTypes": [shared_auth_schema.SharedEntities.User],
        }
    }
    for action in ProvisioningBCActions
}

provisioning_schema = {
    constants.CEDAR_POLICY_NAMESPACE: {
        "entityTypes": {
            **shared_auth_schema.cross_cutting_auth_entities,
        },
        "actions": {**provisioning_bc_actions},
    }
}


def get_full_action_names(names: list[str]) -> str:
    return "[" + ", ".join([f'{constants.CEDAR_POLICY_NAMESPACE}::Action::"{name}"' for name in names]) + "]"
