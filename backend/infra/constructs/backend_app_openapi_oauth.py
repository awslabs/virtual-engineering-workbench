import typing

import aws_cdk
import cdk_nag
import constructs
import yaml
from aws_cdk import aws_apigateway, aws_ec2, aws_iam, aws_lambda, aws_logs, aws_ssm, aws_wafv2
from jinja2 import Environment, FileSystemLoader, select_autoescape

from infra import config


class BackendAppOpenApiOauth(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        user_pool_id: str,
        schema_directory: str,
        schema: str,
        api_version: str,
        version_description: str,
        handler: aws_lambda.Function | aws_lambda.Alias | None = None,
        cache_enabled: bool = False,
        waf_acl_arn: typing.Optional[str] = None,
        cache_explicit_disable: typing.List[str] = [],
        endpoint_type: aws_apigateway.EndpointType = aws_apigateway.EndpointType.REGIONAL,
        vpc_endpoint: aws_ec2.IVpcEndpoint | None = None,
    ) -> None:
        super().__init__(scope, id)

        # API Gateway log group
        access_log_group = aws_logs.LogGroup(
            self,
            "BackendAppS2SApiAccessLogGroup",
            log_group_name=app_config.format_resource_name("api-s2s-access-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        # API Gateway Role for invoking Lambda
        handler_arn = None
        apigw_invocation_role_arn = None
        api_role = None
        if handler:
            api_role = aws_iam.Role(
                self,
                "Role",
                role_name=app_config.format_resource_name("s2s-apigw-role"),
                assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
                description="IAM Role to be used by APIgw to invoke the BE lambda functions",
            )
            # Loading ARN value of Lambda functions
            handler_arn = handler.function_arn
            apigw_invocation_role_arn = api_role.role_arn

            # Policy for allowing specific invocation permissions over the corresponding BE function
            api_role.add_to_policy(aws_iam.PolicyStatement(resources=[handler_arn], actions=["lambda:InvokeFunction"]))

        # Populate the template
        self.template_env = Environment(
            loader=FileSystemLoader(schema_directory), autoescape=select_autoescape(enabled_extensions="yaml")
        )
        self.template = self.template_env.get_template(schema)
        rendered_schema_dict = yaml.safe_load(
            self.template.render(
                handler_arn=handler_arn,
                user_pool_id=user_pool_id,
                apigw_invocation_role_arn=apigw_invocation_role_arn,
                cors_origin=f"'{app_config.environment_config['rest-api-cors-origins']}'",
            )
        )

        self._validate_schema_auth(rendered_schema_dict, "OAuth API", no_auth_paths=[])

        method_options_to_disable_cache: typing.Dict[str, aws_apigateway.MethodDeploymentOptions] = {
            key: aws_apigateway.MethodDeploymentOptions(
                caching_enabled=False,
                cache_ttl=aws_cdk.Duration.seconds(0),
            )
            for key in cache_explicit_disable
        }

        # Api Gateway
        self._api = aws_apigateway.SpecRestApi(
            self,
            id,
            api_definition=aws_apigateway.ApiDefinition.from_inline(rendered_schema_dict),
            deploy=True,
            deploy_options=aws_apigateway.StageOptions(
                cache_data_encrypted=True,
                cache_ttl=aws_cdk.Duration.minutes(5),
                caching_enabled=cache_enabled,
                cache_cluster_enabled=cache_enabled,
                cache_cluster_size="0.5" if cache_enabled else None,
                logging_level=aws_apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=app_config.environment == config.Environment.dev,
                metrics_enabled=True,
                tracing_enabled=True,
                access_log_destination=aws_apigateway.LogGroupLogDestination(access_log_group),
                access_log_format=aws_apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
                description=version_description,
                stage_name=api_version,
                method_options=method_options_to_disable_cache,
            ),
            endpoint_types=[endpoint_type],
            fail_on_warnings=True,
            policy=(
                aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=["execute-api:Invoke"],
                            conditions={
                                "StringEquals": {
                                    "aws:sourceVpce": vpc_endpoint.vpc_endpoint_id,
                                },
                            },
                            effect=aws_iam.Effect.ALLOW,
                            principals=[aws_iam.StarPrincipal()],
                            resources=["execute-api:/*"],
                        ),
                    ]
                )
                if endpoint_type == aws_apigateway.EndpointType.PRIVATE
                else None
            ),
            rest_api_name=app_config.format_resource_name("s2s-api"),
        )

        if endpoint_type == aws_apigateway.EndpointType.PRIVATE:
            self._api.node.default_child.add_property_override(
                "EndpointConfiguration.VpcEndpointIds",
                [vpc_endpoint.vpc_endpoint_id],
            )

        stack = aws_cdk.Stack.of(self)

        if waf_acl_arn:
            aws_wafv2.CfnWebACLAssociation(
                self,
                "WAFACLAssociation",
                web_acl_arn=waf_acl_arn,
                resource_arn=self._api.deployment_stage.stage_arn,
            )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-ApiIdSsmParameter",
            parameter_name=f"/{app_config.format_resource_name('s2s-api')}/api/id",
            description=f"{app_config.component_name} API Id",
            string_value=self._api.rest_api_id,
        )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-ApiUrl",
            parameter_name=f"/{app_config.format_resource_name('s2s-api')}/api/url",
            description=f"{app_config.component_name} API url",
            string_value=self._api.url_for_path(),
        )

        aws_cdk.CfnOutput(
            self,
            "S2sApiUrlOutput",
            value=self._api.url_for_path(),
            description="Invoke URL of the API.",
        )

        # log group suppression
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

        # api suppression
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._api,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG2",
                    reason="Request validation is enabled in OpenAPI schema.",
                ),
            ],
        )

        # policy suppression
        if api_role:
            api_role_policies = [p for p in api_role.node.children if isinstance(p, aws_iam.Policy)]
            if api_role_policies:
                cdk_nag.NagSuppressions.add_resource_suppressions(
                    construct=api_role_policies[0],
                    suppressions=[
                        cdk_nag.NagPackSuppression(
                            id="NIST.800.53.R4-IAMNoInlinePolicy",
                            reason="Using inline policies are enough for the use case.",
                        ),
                        cdk_nag.NagPackSuppression(
                            id="NIST.800.53.R5-IAMNoInlinePolicy",
                            reason="Using inline policies are enough for the use case.",
                        ),
                        cdk_nag.NagPackSuppression(
                            id="PCI.DSS.321-IAMNoInlinePolicy",
                            reason="Using inline policies are enough for the use case.",
                        ),
                    ],
                )

        # stage suppression
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._api.deployment_stage,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG3",
                    reason="AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-APIGWAssociatedWithWAF",
                    reason="AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-APIGWAssociatedWithWAF",
                    reason="AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-APIGWSSLEnabled",
                    reason="Stage is using the default SSL certificate.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-APIGWSSLEnabled",
                    reason="Stage is using the default SSL certificate.",
                ),
            ],
        )

        if not cache_enabled:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=self._api.deployment_stage,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R4-APIGWCacheEnabledAndEncrypted",
                        reason="Cache for API is disabled.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R5-APIGWCacheEnabledAndEncrypted",
                        reason="Cache for API is disabled.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="PCI.DSS.321-APIGWCacheEnabledAndEncrypted",
                        reason="Cache for API is disabled.",
                    ),
                ],
            )

        # CloudWatch role suppression
        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=stack,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AmazonAPIGatewayPushToCloudWatchLogs is enough for API Gateway to write logs to CloudWatch.",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                    ],
                ),
            ],
        )

    def _validate_schema_auth(self, schema_dict, api_name, no_auth_paths=None):
        no_auth_paths = no_auth_paths or []
        security_schemes = set(schema_dict.get("components", {}).get("securitySchemes", {}).keys())
        methods_wo_auth = self._find_methods_without_auth(schema_dict, security_schemes, no_auth_paths)
        if methods_wo_auth:
            raise ValueError(f"{api_name} schema validation failed: Methods without auth detected: {methods_wo_auth}")

    def _find_methods_without_auth(self, schema_dict, security_schemes, no_auth_paths):
        methods_wo_auth = {}
        for path, path_data in schema_dict.get("paths", {}).items():
            if path in no_auth_paths:
                continue
            for method, method_data in path_data.items():
                if isinstance(method_data, dict) and method != "options":
                    auth = method_data.get("security", [])
                    if not auth or not {a for aa in auth for a in aa.keys()}.issubset(security_schemes):
                        if path not in methods_wo_auth:
                            methods_wo_auth[path] = []
                        methods_wo_auth[path].append(method)
        return methods_wo_auth

    @property
    def api(self) -> aws_apigateway.SpecRestApi:
        return self._api
