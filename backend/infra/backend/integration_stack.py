from dataclasses import dataclass

import aws_cdk
import constructs
from aws_cdk import aws_apigateway, aws_certificatemanager, aws_cognito, aws_secretsmanager, aws_ssm

from infra import config
from infra.constructs import private_api_gw_alb


@dataclass
class ApiToPathMapping:
    api: aws_apigateway.IRestApi
    base_path: str


@dataclass
class ApiIntegrationMapping:
    domain_name: str
    cert_arn: str
    mappings: list[ApiToPathMapping]


class ApiIntegrationStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        api_integration_mapping: ApiIntegrationMapping,
        app_config: config.AppConfig,
        provision_private_endpoint: bool = False,
        vpc_endpoint_ips: list[str] | None = None,
        setup_oauth_client: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self._handle_input_validation_errors(api_integration_mapping)

        # Load certificate for the custom domain
        certificate = aws_certificatemanager.Certificate.from_certificate_arn(
            scope=self, id="Certificate", certificate_arn=api_integration_mapping.cert_arn
        )

        # Register the custom domain
        domain = aws_apigateway.DomainName(
            scope=self,
            id="CustomDomain",
            certificate=certificate,
            domain_name=api_integration_mapping.domain_name,
            security_policy=aws_apigateway.SecurityPolicy.TLS_1_2,
        )

        # Assign APIs to corresponding base path
        for mapping in api_integration_mapping.mappings:
            (
                domain.add_api_mapping(target_stage=mapping.api.deployment_stage, base_path=mapping.base_path)
                if "/" in mapping.base_path
                else domain.add_base_path_mapping(mapping.api, base_path=mapping.base_path)
            )
            aws_cdk.CfnOutput(
                scope=self,
                id=f"{mapping.base_path}CustomDomainForApI",
                value=f"{api_integration_mapping.domain_name}/{mapping.base_path}",
                description=f"Custom domain to access {mapping.base_path}",
            )

        # Provision the private endpoint
        if provision_private_endpoint:
            private_api_gw_alb.PrivateApiGwAlb(
                self,
                "PrivateApiGwALB",
                app_config=app_config,
                certificate=certificate,
                vpc_endpoint_ips=vpc_endpoint_ips,
            )

        if setup_oauth_client:
            # Import user pool
            user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
                self,
                app_config.environment_config["cognito-userpool-id-ssm-param"].format(
                    environment=app_config.environment
                ),
            )
            pool = aws_cognito.UserPool.from_user_pool_id(self, "BackendAppUserPool", user_pool_id)

            # Define scope
            packaging_scope = aws_cognito.OAuthScope(
                scope_name="packaging.write", scope_description="Scope for creating resources in Packaging BC."
            )
            publishing_scope = aws_cognito.OAuthScope(
                scope_name="publishing.write", scope_description="Scope for creating resources in Publishing BC."
            )
            projects_scope = aws_cognito.OAuthScope(
                scope_name="projects.write", scope_description="Scope for creating resources in Projects BC."
            )

            # Get client mappings
            client_mappings = (
                [m for m in api_integration_mapping.mappings if m.base_path.startswith("clients/packaging")]
                + [m for m in api_integration_mapping.mappings if m.base_path.startswith("clients/publishing")]
                + [m for m in api_integration_mapping.mappings if m.base_path.startswith("clients/projects")]
            )

            # Add resource servers
            for mapping in client_mappings:
                backend_server = pool.add_resource_server(
                    id="BackendAppResourceServer",
                    identifier=mapping.base_path,
                    scopes=[packaging_scope, publishing_scope],
                    user_pool_resource_server_name=mapping.base_path.replace("/", "."),
                )

            # OAuth settings
            o_auth_settings = aws_cognito.OAuthSettings(
                flows=aws_cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    aws_cognito.OAuthScope.resource_server(server=backend_server, scope=packaging_scope),
                    aws_cognito.OAuthScope.resource_server(server=backend_server, scope=publishing_scope),
                    aws_cognito.OAuthScope.resource_server(server=backend_server, scope=projects_scope),
                ],
            )

            # Add client
            user_pool_client = pool.add_client(
                "workshop-client",
                auth_flows=aws_cognito.AuthFlow(
                    user_password=False,
                    user_srp=False,
                    admin_user_password=False,
                    custom=False,
                ),
                o_auth=o_auth_settings,
                generate_secret=True,
                user_pool_client_name="WorkshopClient",
            )

            # Store secret
            aws_secretsmanager.Secret(
                self,
                "WorkshopClientSecret",
                description="OAuth 2.0 Client ID and secret for the workshop client",
                secret_name=f"/{app_config.format_resource_name('workshop-client-secret')}",
                secret_object_value={
                    "client-id": user_pool_client.user_pool_client_id,
                    "client-secret": user_pool_client.user_pool_client_secret,
                    "client-name": user_pool_client.user_pool_client_name,
                },
            )

    def _handle_input_validation_errors(self, api_integration_mapping: ApiIntegrationMapping):
        if not api_integration_mapping.cert_arn:
            raise ValueError("ARN for certificate is empty string")

        if not api_integration_mapping.domain_name:
            raise ValueError("Domain name is empty")

        if not api_integration_mapping.mappings:
            raise ValueError("List of api to base path mapping is empty")
