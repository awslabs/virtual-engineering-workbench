from infra import config
from infra.auth import packaging_auth_schema
from infra.constructs import backend_app_api_auth

packaging_bc_auth_policies: list[backend_app_api_auth.CedarPolicy] = [
    backend_app_api_auth.CedarPolicy(
        description="Allows admins to creaate and update the mandatory component list",
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.CreateMandatoryComponentsList,
                    packaging_auth_schema.PackagingBCActions.UpdateMandatoryComponentsList,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.ADMINS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows product contributors permissions to archive/create/update components, versions, recipes and pipelines",
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.ArchiveComponent,
                    packaging_auth_schema.PackagingBCActions.ArchiveRecipe,
                    packaging_auth_schema.PackagingBCActions.CreateComponent,
                    packaging_auth_schema.PackagingBCActions.CreateComponentVersion,
                    packaging_auth_schema.PackagingBCActions.CreateImage,
                    packaging_auth_schema.PackagingBCActions.CreatePipeline,
                    packaging_auth_schema.PackagingBCActions.CreateRecipe,
                    packaging_auth_schema.PackagingBCActions.CreateRecipeVersion,
                    packaging_auth_schema.PackagingBCActions.GetComponent,
                    packaging_auth_schema.PackagingBCActions.GetComponentVersion,
                    packaging_auth_schema.PackagingBCActions.GetComponentVersions,
                    packaging_auth_schema.PackagingBCActions.GetComponentVersionTestExecutionLogsUrl,
                    packaging_auth_schema.PackagingBCActions.GetComponentVersionTestExecutions,
                    packaging_auth_schema.PackagingBCActions.GetComponents,
                    packaging_auth_schema.PackagingBCActions.GetComponentsVersions,
                    packaging_auth_schema.PackagingBCActions.GetImage,
                    packaging_auth_schema.PackagingBCActions.GetImages,
                    packaging_auth_schema.PackagingBCActions.GetMandatoryComponentsList,
                    packaging_auth_schema.PackagingBCActions.GetMandatoryComponentsLists,
                    packaging_auth_schema.PackagingBCActions.GetPipeline,
                    packaging_auth_schema.PackagingBCActions.GetPipelines,
                    packaging_auth_schema.PackagingBCActions.GetPipelinesAllowedBuildTypes,
                    packaging_auth_schema.PackagingBCActions.GetRecipe,
                    packaging_auth_schema.PackagingBCActions.GetRecipeVersion,
                    packaging_auth_schema.PackagingBCActions.GetRecipeVersions,
                    packaging_auth_schema.PackagingBCActions.GetRecipeVersionTestExecutionLogsUrl,
                    packaging_auth_schema.PackagingBCActions.GetRecipeVersionTestExecutions,
                    packaging_auth_schema.PackagingBCActions.GetRecipes,
                    packaging_auth_schema.PackagingBCActions.GetRecipesVersions,
                    packaging_auth_schema.PackagingBCActions.ReleaseComponentVersion,
                    packaging_auth_schema.PackagingBCActions.ReleaseRecipeVersion,
                    packaging_auth_schema.PackagingBCActions.RetireComponentVersion,
                    packaging_auth_schema.PackagingBCActions.RetirePipeline,
                    packaging_auth_schema.PackagingBCActions.RetireRecipeVersion,
                    packaging_auth_schema.PackagingBCActions.UpdateComponent,
                    packaging_auth_schema.PackagingBCActions.UpdateComponentVersion,
                    packaging_auth_schema.PackagingBCActions.UpdatePipeline,
                    packaging_auth_schema.PackagingBCActions.UpdateRecipeVersion,
                    packaging_auth_schema.PackagingBCActions.ValidateComponentVersion,
                    packaging_auth_schema.PackagingBCActions.GenerateComponentVersionDefinition,
                    packaging_auth_schema.PackagingBCActions.GetComponentVersionDefinitionGenerationStatus,

                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PRODUCT_CONTRIBUTORS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows Program Owners to share components",
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.ShareComponent,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PROGRAM_OWNERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows Power Users to retire pipelines",
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.RetirePipeline,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.POWER_USERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows all authenticated principals to get Swagger API spec.",
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.GetSwaggerSpec,
                ])},
                resource
            );
    """,
    ),
]
