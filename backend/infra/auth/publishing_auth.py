from infra import config
from infra.auth import publishing_auth_schema
from infra.constructs import backend_app_api_auth

publishing_bc_auth_policies: list[backend_app_api_auth.CedarPolicy] = [
    backend_app_api_auth.CedarPolicy(
        description="Allows program owners to archive products.",
        statement=f"""
            permit (
                principal,
                action in {publishing_auth_schema.get_full_action_names([
                    publishing_auth_schema.PublishingBCActions.ArchiveProduct,

                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PROGRAM_OWNERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows contributors access to Publishing features.",
        statement=f"""
            permit (
                principal,
                action in {publishing_auth_schema.get_full_action_names([
                        publishing_auth_schema.PublishingBCActions.CreateProduct,
                        publishing_auth_schema.PublishingBCActions.CreateProductVersion,
                        publishing_auth_schema.PublishingBCActions.GetAmis,
                        publishing_auth_schema.PublishingBCActions.GetAvailableContainerImages,
                        publishing_auth_schema.PublishingBCActions.GetAvailableProductVersions,
                        publishing_auth_schema.PublishingBCActions.GetLatestMajorVersions,
                        publishing_auth_schema.PublishingBCActions.GetLatestTemplate,
                        publishing_auth_schema.PublishingBCActions.GetProduct,
                        publishing_auth_schema.PublishingBCActions.GetProducts,
                        publishing_auth_schema.PublishingBCActions.GetProductVersion,
                        publishing_auth_schema.PublishingBCActions.PromoteProductVersion,
                        publishing_auth_schema.PublishingBCActions.RestoreProductVersion,
                        publishing_auth_schema.PublishingBCActions.RetireProductVersion,
                        publishing_auth_schema.PublishingBCActions.RetryProductVersion,
                        publishing_auth_schema.PublishingBCActions.SetRecommendedVersion,
                        publishing_auth_schema.PublishingBCActions.UpdateProductVersion,
                        publishing_auth_schema.PublishingBCActions.ValidateProductVersion,

                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PRODUCT_CONTRIBUTORS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows users to get available Products.",
        statement=f"""
            permit (
                principal,
                action in {publishing_auth_schema.get_full_action_names([
                    publishing_auth_schema.PublishingBCActions.GetAvailableProducts
                ])},
                resource
            )
            when {{ principal in {config.CedarResourceAttribute.PLATFORM_USERS} }};
    """,
    ),
    backend_app_api_auth.CedarPolicy(
        description="Allows all authenticated principals to get Swagger API spec.",
        statement=f"""
            permit (
                principal,
                action in {publishing_auth_schema.get_full_action_names([
                    publishing_auth_schema.PublishingBCActions.GetSwaggerSpec,
                ])},
                resource
            );
    """,
    ),
]
