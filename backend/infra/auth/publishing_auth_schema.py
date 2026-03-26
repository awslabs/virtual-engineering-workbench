import enum

from infra import constants
from infra.auth import shared_auth_schema


class PublishingBCActions(enum.StrEnum):
    ArchiveProduct = "ArchiveProduct"
    CreateProduct = "CreateProduct"
    CreateProductVersion = "CreateProductVersion"
    GetAmis = "GetAmis"
    GetAvailableContainerImages = "GetAvailableContainerImages"
    GetAvailableProducts = "GetAvailableProducts"
    GetAvailableProductVersions = "GetAvailableProductVersions"
    GetAvailableProductVersionsInternal = "GetAvailableProductVersionsInternal"
    GetLatestMajorVersions = "GetLatestMajorVersions"
    GetLatestTemplate = "GetLatestTemplate"
    GetProduct = "GetProduct"
    GetProducts = "GetProducts"
    GetProductVersion = "GetProductVersion"
    GetProductVersionDistribution = "GetProductVersionDistribution"
    GetPublishedAmis = "GetPublishedAmis"
    GetSwaggerSpec = "GetSwaggerSpec"
    PromoteProductVersion = "PromoteProductVersion"
    RestoreProductVersion = "RestoreProductVersion"
    RetireProductVersion = "RetireProductVersion"
    RetryProductVersion = "RetryProductVersion"
    SetRecommendedVersion = "SetRecommendedVersion"
    UpdateProductVersion = "UpdateProductVersion"
    ValidateProductVersion = "ValidateProductVersion"


publishing_bc_actions = {
    action.value: {
        "appliesTo": {
            "resourceTypes": [
                shared_auth_schema.SharedEntities.Project,
            ],
            "principalTypes": [shared_auth_schema.SharedEntities.User],
        }
    }
    for action in PublishingBCActions
}

publishing_schema = {
    constants.CEDAR_POLICY_NAMESPACE: {
        "entityTypes": {
            **shared_auth_schema.cross_cutting_auth_entities,
        },
        "actions": {**publishing_bc_actions},
    }
}


def get_full_action_names(names: list[str]) -> str:
    return "[" + ", ".join([f'{constants.CEDAR_POLICY_NAMESPACE}::Action::"{name}"' for name in names]) + "]"
