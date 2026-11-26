from infra import config
from infra.auth import packaging_auth_schema, shared_auth_schema
from infra.constructs import backend_app_api_auth

packaging_bc_auth_policies: list[backend_app_api_auth.CedarPolicy] = [
    backend_app_api_auth.CedarPolicy(
        description="Allows admins to create and update the mandatory component list",
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
        description=("Allows project admins to browse Marketplace offers and request a quote."),
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.ListMarketplacePurchaseOptions,
                    packaging_auth_schema.PackagingBCActions.GetMarketplaceOffer,
                    packaging_auth_schema.PackagingBCActions.CreateMarketplaceQuote,
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.ADMINS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        # The three agreement operations are ACCOUNT-scoped, so they cannot be
        # authorized against a project. An AWS Marketplace agreement is an
        # account-level resource: the buyer account holds one set of
        # subscriptions and AWS exposes no project dimension on them. Their
        # routes therefore carry no `/projects/<project_id>/` prefix, and the
        # authorizer only resolves a `VEW::Project` resource entity for paths
        # that start with `/projects/` -- so a `resource.admins` condition
        # could never be satisfied here and would hard-deny every call.
        #
        # Authorize on the principal instead, matching the existing
        # account-level `CreateProject` policy in the projects BC: permit a
        # user who is an admin of at least one project. This is deliberately
        # a platform-level permission, which is what "may spend this account's
        # money on a Marketplace subscription" actually is.
        # AVP caps Description at 150 characters. A longer one fails
        # CloudFormation change-set validation at deploy time, which unit
        # tests do not exercise.
        description=(
            "Allows admins of at least one project to accept, list and cancel the buyer "
            "account's Marketplace agreements. Account-scoped, not project resources."
        ),
        statement=f"""
            permit (
                principal,
                action in {packaging_auth_schema.get_full_action_names([
                    packaging_auth_schema.PackagingBCActions.AcceptMarketplaceQuote,
                    packaging_auth_schema.PackagingBCActions.CancelMarketplaceAgreement,
                    packaging_auth_schema.PackagingBCActions.ListMarketplaceAgreements,
                ])},
                resource
            )
            when {{
                principal has {shared_auth_schema.SharedAttributes.TotalAdminAssignments}
                && principal.{shared_auth_schema.SharedAttributes.TotalAdminAssignments} > 0
            }};
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
                    packaging_auth_schema.PackagingBCActions.ImportImage,
                    packaging_auth_schema.PackagingBCActions.ResolveAwsPublishedAmi,
                    packaging_auth_schema.PackagingBCActions.ListImportableAmis,
                    packaging_auth_schema.PackagingBCActions.DiscoverMarketplaceSubscriptions,
                    packaging_auth_schema.PackagingBCActions.SearchMarketplaceListings,
                    packaging_auth_schema.PackagingBCActions.GetMarketplaceListing,
                    packaging_auth_schema.PackagingBCActions.GetMarketplaceFacets,
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
