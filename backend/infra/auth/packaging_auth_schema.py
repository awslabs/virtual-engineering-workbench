import enum

from infra import constants
from infra.auth import shared_auth_schema


class PackagingBCActions(enum.StrEnum):
    ArchiveComponent = "ArchiveComponent"
    ArchiveRecipe = "ArchiveRecipe"
    CreateComponent = "CreateComponent"
    CreateComponentVersion = "CreateComponentVersion"
    CreateImage = "CreateImage"
    CreateMandatoryComponentsList = "CreateMandatoryComponentsList"
    CreatePipeline = "CreatePipeline"
    CreateRecipe = "CreateRecipe"
    CreateRecipeVersion = "CreateRecipeVersion"
    GetComponent = "GetComponent"
    GetComponents = "GetComponents"
    GetComponentsVersions = "GetComponentsVersions"
    GetComponentVersion = "GetComponentVersion"
    GetComponentVersions = "GetComponentVersions"
    GetComponentVersionTestExecutions = "GetComponentVersionTestExecutions"
    GetComponentVersionTestExecutionLogsUrl = "GetComponentVersionTestExecutionLogsUrl"
    GetImage = "GetImage"
    GetImages = "GetImages"
    GetMandatoryComponentsList = "GetMandatoryComponentsList"
    GetMandatoryComponentsLists = "GetMandatoryComponentsLists"
    GetPipeline = "GetPipeline"
    GetPipelines = "GetPipelines"
    GetPipelinesAllowedBuildTypes = "GetPipelinesAllowedBuildTypes"
    GetRecipe = "GetRecipe"
    GetRecipes = "GetRecipes"
    GetRecipesVersions = "GetRecipesVersions"
    GetRecipeVersion = "GetRecipeVersion"
    GetRecipeVersions = "GetRecipeVersions"
    GetRecipeVersionTestExecutions = "GetRecipeVersionTestExecutions"
    GetRecipeVersionTestExecutionLogsUrl = "GetRecipeVersionTestExecutionLogsUrl"
    GetSwaggerSpec = "GetSwaggerSpec"
    ReleaseComponentVersion = "ReleaseComponentVersion"
    ReleaseRecipeVersion = "ReleaseRecipeVersion"
    RetireComponentVersion = "RetireComponentVersion"
    RetirePipeline = "RetirePipeline"
    RetireRecipeVersion = "RetireRecipeVersion"
    ShareComponent = "ShareComponent"
    UpdateComponent = "UpdateComponent"
    UpdateComponentVersion = "UpdateComponentVersion"
    UpdateMandatoryComponentsList = "UpdateMandatoryComponentsList"
    UpdatePipeline = "UpdatePipeline"
    UpdateRecipeVersion = "UpdateRecipeVersion"
    ValidateComponentVersion = "ValidateComponentVersion"
    GenerateComponentVersionDefinition = "GenerateComponentVersionDefinition"
    GetComponentVersionDefinitionGenerationStatus = "GetComponentVersionDefinitionGenerationStatus"


packaging_bc_actions = {
    action.value: {
        "appliesTo": {
            "resourceTypes": [
                shared_auth_schema.SharedEntities.Project,
            ],
            "principalTypes": [shared_auth_schema.SharedEntities.User],
        }
    }
    for action in PackagingBCActions
}

packaging_schema = {
    constants.CEDAR_POLICY_NAMESPACE: {
        "entityTypes": {
            **shared_auth_schema.cross_cutting_auth_entities,
        },
        "actions": {**packaging_bc_actions},
    }
}


def get_full_action_names(names: list[str]) -> str:
    return "[" + ", ".join([f'{constants.CEDAR_POLICY_NAMESPACE}::Action::"{name}"' for name in names]) + "]"
