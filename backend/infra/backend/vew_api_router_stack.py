from __future__ import annotations

import json
import typing

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_apigatewayv2, aws_apigatewayv2_authorizers, aws_apigatewayv2_integrations, aws_logs, aws_ssm

from infra import config


class VewApiRouterStack(aws_cdk.Stack):
    """Path-based routing layer for the ``vew`` CLI.

    The CLI expects a single API endpoint that forwards ``/{bounded-context}/*``
    to the matching backend API Gateway. The deploy provisions one execute-api
    Gateway per bounded context, so this stack fronts them and provides the
    unified URL the CLI's config expects.

    Only needed when the deploy has no custom API domain. With one configured,
    :class:`infra.backend.integration_stack.ApiIntegrationStack` already fronts
    the per-BC gateways under a single host via API Gateway base path mappings,
    and ``backend_app.py`` skips registering this stack.

    Reads each bounded context's user-facing API URL from the SSM parameter its
    own stack publishes, and creates an ``ANY /{bc}/{proxy+}`` route per context.

    Every route is protected by a JWT authorizer validating the CLI's Cognito
    access token. The per-BC REST APIs behind this stack continue to run their
    own Cedar authorization on the same token, so this is defence in depth:
    unauthenticated traffic never reaches a backend Lambda authorizer.

    Publishes the resulting URL as CloudFormation output ``VewApiEndpoint``.
    deploy.sh copies that into ``/<app-name>-<env>/vew-api-endpoint``, which is
    what the CLI reads for ``api_endpoint``, and writes the custom-domain URL
    into the same parameter when this stack is not deployed. Keeping deploy.sh as
    the only writer means the CLI never has to know which mode it is running
    against, and switching modes cannot collide on the parameter name.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        bounded_contexts: list[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        if not bounded_contexts:
            raise ValueError("VewApiRouterStack requires at least one bounded context to route.")

        self._app_config = app_config

        http_api = aws_apigatewayv2.HttpApi(
            self,
            "VewApiRouter",
            api_name=app_config.format_base_resource_name("vew-api-router"),
            description="Path-based routing for the vew CLI. Fronts per-bounded-context API Gateways.",
        )

        self._configure_access_logging(http_api)
        authorizer = self._build_authorizer(app_config)

        for bounded_context in bounded_contexts:
            # Resolved by CloudFormation at deploy time, so the bounded context's
            # own stack must already have published this parameter. backend_app.py
            # registers this stack after the bounded contexts for that reason.
            bc_api_url = aws_ssm.StringParameter.value_for_string_parameter(
                self,
                f"/{app_config.format_resource_name_with_component(bounded_context, 'api')}/api/url",
            )

            # The bounded context URL is https://<id>.execute-api.<region>.amazonaws.com/v1/.
            # Appending {proxy} — the API Gateway v2 URI substitution placeholder that
            # matches the wildcard in the route key /{bc}/{proxy+} — preserves the
            # proxied path. Query strings pass through automatically on HTTP APIs,
            # unlike REST APIs.
            http_api.add_routes(
                path=f"/{bounded_context}/{{proxy+}}",
                methods=[aws_apigatewayv2.HttpMethod.ANY],
                integration=aws_apigatewayv2_integrations.HttpUrlIntegration(
                    f"{bounded_context}-integration",
                    f"{bc_api_url}{{proxy}}",
                ),
                authorizer=authorizer,
            )

        endpoint = http_api.api_endpoint

        # This stack deliberately does NOT write the /<app>-<env>/vew-api-endpoint
        # SSM parameter the CLI reads. deploy.sh owns that parameter in both deploy
        # modes: it publishes the VewApiEndpoint output below when the router is
        # deployed, and the custom-domain URL when ApiIntegrationStack provides the
        # unified host instead.
        #
        # A stack-owned parameter would turn a mode switch into a deploy failure.
        # An environment that started with a custom API domain already has the
        # parameter, created out of band, and CloudFormation cannot create one
        # whose name exists — it would fail at deploy time with a clean synth. One
        # owner across both modes removes that transition entirely.
        aws_cdk.CfnOutput(
            self,
            "VewApiEndpoint",
            export_name=f"{self.stack_name}-VewApiEndpoint",
            description="Unified API endpoint for the vew CLI (routes /{bc}/* to per-BC API Gateways)",
            value=endpoint,
        )

        aws_cdk.CfnOutput(
            self,
            "VewApiRoutedBoundedContexts",
            export_name=f"{self.stack_name}-VewApiRoutedBoundedContexts",
            description="Bounded contexts wired into the vew CLI routing layer",
            value=",".join(bounded_contexts),
        )

    def _configure_access_logging(self, http_api: aws_apigatewayv2.HttpApi) -> None:
        """Enable access logging on the default stage (cdk-nag AwsSolutions-APIG1).

        HttpApi's L2 does not surface access log settings, so this reaches through
        to the underlying CfnStage.
        """
        access_log_group = aws_logs.LogGroup(
            self,
            "VewApiAccessLogs",
            log_group_name=self._app_config.format_resource_name("access-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )
        # Same position the other backend log groups take: CloudWatch Logs encrypts
        # at rest with an AWS-owned key, and these packs require a customer-managed
        # KMS key specifically. See backend_app_event_bus.py for the precedent.
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=access_log_group,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
            ],
        )
        default_stage = typing.cast(
            aws_apigatewayv2.CfnStage,
            http_api.default_stage.node.default_child,  # type: ignore[union-attr]
        )
        default_stage.access_log_settings = aws_apigatewayv2.CfnStage.AccessLogSettingsProperty(
            destination_arn=access_log_group.log_group_arn,
            format=json.dumps(
                {
                    "requestId": "$context.requestId",
                    "ip": "$context.identity.sourceIp",
                    "requestTime": "$context.requestTime",
                    "httpMethod": "$context.httpMethod",
                    "routeKey": "$context.routeKey",
                    "status": "$context.status",
                    "protocol": "$context.protocol",
                    "responseLength": "$context.responseLength",
                }
            ),
        )

    def _build_authorizer(self, app_config: config.AppConfig) -> aws_apigatewayv2_authorizers.HttpJwtAuthorizer:
        """JWT authorizer validating the Cognito access token the CLI presents.

        Both parameters read here are published by the frontend user pool
        construct (AppCdn on the public access path, AppElb on the private one).
        Do not create them here: a second AWS::SSM::Parameter with the same Name
        passes synth but fails at CloudFormation deploy time with a name
        collision. That mistake has already been made and reverted once.
        """
        environment = app_config.environment

        user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=environment),
        )
        vew_cli_client_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-vew-cli-client-id-ssm-param"].format(environment=environment),
        )

        # Region comes from config rather than self.region, matching how the
        # authorization stack builds the same issuer. deploy.sh patches
        # `cognito-region` to the deployment region, so in practice the two agree;
        # note the user-pool-id lookup above is a same-region SSM read, so a
        # genuinely cross-region user pool would need that parameter replicated
        # before this would compose.
        cognito_region = app_config.environment_config["cognito-region"]
        jwt_issuer = f"https://cognito-idp.{cognito_region}.amazonaws.com/{user_pool_id}"

        # The CLI presents a Cognito *access* token (cli/src/identity/domain/service.rs
        # returns tokens.access_token). Access tokens carry `client_id` and no `aud`
        # claim, and API Gateway validates `client_id` against jwtAudience when `aud`
        # is absent — so the app client id is the correct audience value here.
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html
        return aws_apigatewayv2_authorizers.HttpJwtAuthorizer(
            "VewCliAuthorizer",
            jwt_issuer,
            authorizer_name=app_config.format_base_resource_name("vew-cli-authorizer"),
            jwt_audience=[vew_cli_client_id],
        )
