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
    DiscoverMarketplaceSubscriptions = "DiscoverMarketplaceSubscriptions"
    # Marketplace procurement actions. Gated to admins because they can
    # commit real money to AWS Marketplace agreements.
    ListMarketplacePurchaseOptions = "ListMarketplacePurchaseOptions"
    GetMarketplaceOffer = "GetMarketplaceOffer"
    CreateMarketplaceQuote = "CreateMarketplaceQuote"
    AcceptMarketplaceQuote = "AcceptMarketplaceQuote"
    CancelMarketplaceAgreement = "CancelMarketplaceAgreement"
    ListMarketplaceAgreements = "ListMarketplaceAgreements"
    # Public-catalog browse actions. Read-only, no money moves —
    # commitment happens through the accept-quote flow.
    SearchMarketplaceListings = "SearchMarketplaceListings"
    GetMarketplaceListing = "GetMarketplaceListing"
    GetMarketplaceFacets = "GetMarketplaceFacets"
    GenerateComponentVersionDefinition = "GenerateComponentVersionDefinition"
    GetComponent = "GetComponent"
    GetComponents = "GetComponents"
    GetComponentsVersions = "GetComponentsVersions"
    GetComponentVersion = "GetComponentVersion"
    GetComponentVersionDefinitionGenerationStatus = "GetComponentVersionDefinitionGenerationStatus"
    GetComponentVersions = "GetComponentVersions"
    GetComponentVersionTestExecutionLogsUrl = "GetComponentVersionTestExecutionLogsUrl"
    GetComponentVersionTestExecutions = "GetComponentVersionTestExecutions"
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
    GetRecipeVersionTestExecutionLogsUrl = "GetRecipeVersionTestExecutionLogsUrl"
    GetRecipeVersionTestExecutions = "GetRecipeVersionTestExecutions"
    GetSwaggerSpec = "GetSwaggerSpec"
    ImportImage = "ImportImage"
    ListImportableAmis = "ListImportableAmis"
    ReleaseComponentVersion = "ReleaseComponentVersion"
    # Read-only: resolves an AWS-published listing to AMI candidates. Granted
    # alongside ImportImage, but separate so the permission says what it does.
    ResolveAwsPublishedAmi = "ResolveAwsPublishedAmi"
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
