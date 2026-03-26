from dataclasses import dataclass

import constructs
from aws_cdk import aws_cognito

from infra import config
from infra.constructs import backend_app_api_resource_server


@dataclass
class AppClientResourceServer:
    resource_server: backend_app_api_resource_server.BackendAppApiResourceServer
    scopes: list[str] | None


class BackendAppApiOAuthClient(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        user_pool: aws_cognito.IUserPool,
        resource_servers: list[AppClientResourceServer],
        client_name: str,
        custom_oauth_settings: aws_cognito.OAuthSettings | None = None,
        generate_secret: bool = True,
    ) -> None:
        super().__init__(scope, id)

        if custom_oauth_settings:
            o_auth_settings = custom_oauth_settings
        else:
            all_scopes = []

            for resource_server in resource_servers:
                all_scopes.extend(
                    [
                        aws_cognito.OAuthScope.resource_server(
                            server=resource_server.resource_server.resource_server, scope=scope
                        )
                        for scope in resource_server.resource_server.scopes
                        if not resource_server.scopes or scope.scope_name in resource_server.scopes
                    ]
                )

            o_auth_settings = aws_cognito.OAuthSettings(
                flows=aws_cognito.OAuthFlows(client_credentials=True),
                scopes=all_scopes,
            )

        # Add client
        user_pool.add_client(
            "OAuthClient",
            auth_flows=aws_cognito.AuthFlow(
                user_password=False,
                user_srp=False,
                admin_user_password=False,
                custom=False,
            ),
            o_auth=o_auth_settings,
            generate_secret=generate_secret,
            user_pool_client_name=app_config.format_resource_name(client_name),
        )
