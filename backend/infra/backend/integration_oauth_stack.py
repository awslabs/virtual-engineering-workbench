import aws_cdk
import constructs
from aws_cdk import aws_cognito, aws_ssm

from infra import config
from infra.constructs import backend_app_api_oauth_client, backend_app_api_resource_server


class IntegrationOauthStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=app_config.environment),
        )

        user_pool = aws_cognito.UserPool.from_user_pool_id(self, "BackendAppUserPool", user_pool_id)

        provisioning_resource_server = backend_app_api_resource_server.BackendAppApiResourceServer(
            self,
            "ProvisioningResourceServer",
            user_pool,
            resource_server=backend_app_api_resource_server.ResourceServer(
                identifier="clients/provisioning",
                scopes={
                    "product.read": "Read access to product catalogue",
                    "provisioned_product.write": "Allows to provision and manipulate provisioned products",
                    "provisioned_product.read": "Allows to get information about provisioned products",
                },
            ),
        )

        provisioning_compound_resource_server = backend_app_api_resource_server.BackendAppApiResourceServer(
            self,
            "ProvisioningCompoundResourceServer",
            user_pool,
            resource_server=backend_app_api_resource_server.ResourceServer(
                identifier="clients/provisioning-compound",
                scopes={
                    "provisioned_product.write": "Allows to provision and manipulate provisioned products",
                    "provisioned_product.read": "Allows to get information about provisioned products",
                },
            ),
        )

        projects_resource_server = backend_app_api_resource_server.BackendAppApiResourceServer(
            self,
            "ProjectsResourceServer",
            user_pool,
            resource_server=backend_app_api_resource_server.ResourceServer(
                identifier="clients/projects",
                scopes={
                    "program.read": "Allows to read project data",
                    "assignment.write": "Allows to enrol users to programs",
                    "assignment.read": "Allows to read user data in the projects",
                },
            ),
        )

        publishing_compound_resource_server = backend_app_api_resource_server.BackendAppApiResourceServer(
            self,
            "PublishingCompoundResourceServer",
            user_pool,
            resource_server=backend_app_api_resource_server.ResourceServer(
                identifier="clients/publishing-compound",
                scopes={
                    "product.read": "Allows to read compound product data",
                    "version.read": "Allows to read compound product version data",
                },
            ),
        )

        backend_app_api_oauth_client.BackendAppApiOAuthClient(
            self,
            "SampleS2SClient",
            app_config=app_config,
            user_pool=user_pool,
            resource_servers=[
                backend_app_api_oauth_client.AppClientResourceServer(
                    resource_server=provisioning_resource_server,
                    scopes=["product.read", "provisioned_product.write", "provisioned_product.read"],
                ),
                backend_app_api_oauth_client.AppClientResourceServer(
                    resource_server=provisioning_compound_resource_server,
                    scopes=["provisioned_product.write", "provisioned_product.read"],
                ),
                backend_app_api_oauth_client.AppClientResourceServer(
                    resource_server=projects_resource_server,
                    scopes=["program.read", "assignment.write", "assignment.read"],
                ),
                backend_app_api_oauth_client.AppClientResourceServer(
                    resource_server=publishing_compound_resource_server,
                    scopes=["product.read", "version.read"],
                ),
            ],
            client_name="sample-s2s",
        )

        # backend_app_api_oauth_client.BackendAppApiOAuthClient(
        #     self,
        #     "AuthCodeFlowClient",
        #     app_config=app_config,
        #     user_pool=user_pool,
        #     resource_servers=[],
        #     client_name="auth-code-flow",
        #     custom_oauth_settings=aws_cognito.OAuthSettings(
        #         flows=aws_cognito.OAuthFlows(authorization_code_grant=True),
        #         scopes=[
        #             aws_cognito.OAuthScope.EMAIL,
        #             aws_cognito.OAuthScope.OPENID,
        #             aws_cognito.OAuthScope.PROFILE,
        #         ],
        #     ),
        #     generate_secret=False,
        # )
