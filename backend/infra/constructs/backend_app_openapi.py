import copy
import datetime
import json
import re
import typing

import aws_cdk
import cdk_nag
import constructs
import yaml
from aws_cdk import (
    Arn,
    ArnFormat,
    aws_apigateway,
    aws_ec2,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_ssm,
    aws_wafv2,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape

from infra import config, constants
from infra.constructs import backend_app_api_auth


def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


class BackendAppOpenApi(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        handler: typing.Union[aws_lambda.Function, aws_lambda.Alias],
        schema_directory: str,
        schema: str,
        api_version: str,
        version_description: str,
        custom_domain: typing.Optional[str],
        base_path: str,
        cache_enabled: bool = False,
        waf_acl_arn: typing.Optional[str] = None,
        cache_explicit_disable: typing.List[str] = [],
        endpoint_type: aws_apigateway.EndpointType = aws_apigateway.EndpointType.REGIONAL,
        vpc_endpoint: aws_ec2.IVpcEndpoint | None = None,
        policy: typing.Optional[aws_iam.PolicyDocument] = None,
        cedar_policy_config: backend_app_api_auth.CedarPolicyConfig | None = None,
        name: str = "api",
        provision_iam_api: bool = False,
        iam_role_access: typing.Optional[str] = None,
        iam_api_resource_policy: typing.Optional[aws_iam.PolicyDocument] = None,
    ) -> None:
        super().__init__(scope, id)

        authorization_bc_handler_arn = self.__get_auth_arn(cedar_policy_config, app_config)

        access_log_group = self._create_log_group(app_config, name)
        api_role = self._create_api_role(app_config, handler, authorization_bc_handler_arn, name)
        handler_arn = handler.function_arn

        rendered_schema_dict = self._prepare_schema(
            schema_directory,
            schema,
            handler_arn,
            authorization_bc_handler_arn,
            api_role,
            app_config,
            custom_domain,
            base_path,
        )

        self._api = self._create_rest_api(
            id,
            app_config,
            rendered_schema_dict,
            access_log_group,
            api_version,
            version_description,
            cache_enabled,
            cache_explicit_disable,
            endpoint_type,
            vpc_endpoint,
            policy,
            name,
        )

        self._configure_vpc_endpoint(endpoint_type, vpc_endpoint)

        backend_app_api_auth.BackendAppAPIAuth(
            self, "AVPAuth", app_config=app_config, cedar_config=cedar_policy_config, api=self._api
        )

        stack = aws_cdk.Stack.of(self)
        self._create_api_outputs(app_config, stack, name, waf_acl_arn)
        self._add_suppressions(access_log_group, api_role, cache_enabled, stack)

        self._iam_api = None
        if provision_iam_api and cedar_policy_config:
            self._iam_api = self._create_iam_api(
                app_config,
                handler_arn,
                api_role,
                api_version,
                version_description,
                cache_enabled,
                waf_acl_arn,
                cache_explicit_disable,
                endpoint_type,
                vpc_endpoint,
                iam_api_resource_policy,
                stack,
                cedar_policy_config,
                iam_role_access,
            )

    def _create_log_group(self, app_config, name, encryption_key=None):
        return aws_logs.LogGroup(
            self,
            "BackendAppApiAccessLogGroup",
            log_group_name=app_config.format_resource_name(f"{name}-access-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
            encryption_key=encryption_key,
        )

    def _create_api_role(self, app_config, handler, authorization_bc_handler_arn, name):
        api_role = aws_iam.Role(
            self,
            "Role",
            role_name=app_config.format_resource_name(f"{name}gw-role"),
            assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="IAM Role to be used by APIgw to invoke the BE lambda functions",
        )
        handler_arns = [handler.function_arn, authorization_bc_handler_arn]
        api_role.add_to_policy(
            aws_iam.PolicyStatement(
                resources=[arn for arn in handler_arns if arn is not None], actions=["lambda:InvokeFunction"]
            )
        )
        return api_role

    def _prepare_schema(
        self,
        schema_directory,
        schema,
        handler_arn,
        authorization_bc_handler_arn,
        api_role,
        app_config,
        custom_domain,
        base_path,
    ):
        self.template_env = Environment(
            loader=FileSystemLoader(schema_directory), autoescape=select_autoescape(enabled_extensions="yaml")
        )
        self.template = self.template_env.get_template(schema)
        rendered_schema_dict = yaml.safe_load(
            self.template.render(
                handler_arn=handler_arn,
                authorization_bc_handler_arn=authorization_bc_handler_arn,
                apigw_invocation_role_arn=api_role.role_arn,
                cors_origin=f"'{app_config.environment_config['rest-api-cors-origins']}'",
                handler_region=Arn.split(handler_arn, ArnFormat.COLON_RESOURCE_NAME).region,
            )
        )

        openapi_dict = self._prepare_openapi_dict(rendered_schema_dict, app_config, custom_domain, base_path)
        self._add_openapi_endpoint(rendered_schema_dict, openapi_dict)
        self._validate_schema_auth(
            rendered_schema_dict,
            "REST API",
            no_auth_paths=[
                "/authenticate",
                "/resolveSession",
                "/vs-code/authenticate",
                "/vs-code/resolve",
                "/webhooks/github",
            ],
        )
        return rendered_schema_dict

    def _prepare_openapi_dict(self, rendered_schema_dict, app_config, custom_domain, base_path):
        openapi_dict = copy.deepcopy(rendered_schema_dict)
        openapi_dict["info"]["title"] = app_config.format_resource_name("api")

        if custom_domain and base_path:
            openapi_dict["servers"] = [{"url": f"https://{custom_domain}/{base_path}"}]

        for path in openapi_dict["paths"]:
            for method in openapi_dict["paths"][path]:
                if "tags" in openapi_dict["paths"][path][method]:
                    del openapi_dict["paths"][path][method]["tags"]
        return openapi_dict

    def _add_openapi_endpoint(self, rendered_schema_dict, openapi_dict):
        rendered_schema_dict["paths"]["openapi.json"] = {
            "get": {
                "operationId": "openapi",
                "responses": {
                    "200": {
                        "description": "200 response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Empty"}}},
                    }
                },
                "security": [{"sigv4": []}],
                "x-amazon-apigateway-integration": {
                    "responses": {
                        "default": {
                            "statusCode": "200",
                            "responseTemplates": {
                                "application/json": "#[[\n"
                                + json.dumps(openapi_dict, default=serialize_datetime)
                                + "\n]]#"
                            },
                        }
                    },
                    "requestTemplates": {"application/json": '{"statusCode": 200}'},
                    "passthroughBehavior": "when_no_match",
                    "type": "mock",
                },
            }
        }
        rendered_schema_dict["components"]["securitySchemes"]["sigv4"] = {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "x-amazon-apigateway-authtype": "awsSigv4",
        }

    def _create_rest_api(
        self,
        id,
        app_config,
        rendered_schema_dict,
        access_log_group,
        api_version,
        version_description,
        cache_enabled,
        cache_explicit_disable,
        endpoint_type,
        vpc_endpoint,
        policy,
        name,
    ):
        method_options_to_disable_cache = {
            key: aws_apigateway.MethodDeploymentOptions(caching_enabled=False, cache_ttl=aws_cdk.Duration.seconds(0))
            for key in cache_explicit_disable
        }

        return aws_apigateway.SpecRestApi(
            self,
            id,
            api_definition=aws_apigateway.ApiDefinition.from_inline(rendered_schema_dict),
            deploy=True,
            deploy_options=self._create_stage_options(
                access_log_group,
                api_version,
                version_description,
                cache_enabled,
                method_options_to_disable_cache,
                app_config,
            ),
            endpoint_types=[endpoint_type],
            fail_on_warnings=True,
            policy=self.__get_resource_policy(policy, vpc_endpoint, endpoint_type),
            rest_api_name=app_config.format_resource_name("api"),
        )

    def _create_stage_options(
        self,
        access_log_group,
        api_version,
        version_description,
        cache_enabled,
        method_options_to_disable_cache,
        app_config=None,
    ):
        return aws_apigateway.StageOptions(
            cache_data_encrypted=True,
            cache_ttl=aws_cdk.Duration.minutes(5),
            caching_enabled=cache_enabled,
            cache_cluster_enabled=cache_enabled,
            cache_cluster_size="0.5" if cache_enabled else None,
            logging_level=aws_apigateway.MethodLoggingLevel.INFO,
            data_trace_enabled=app_config is not None and app_config.environment == config.Environment.dev,
            metrics_enabled=True,
            tracing_enabled=True,
            access_log_destination=aws_apigateway.LogGroupLogDestination(access_log_group),
            access_log_format=aws_apigateway.AccessLogFormat.custom(
                json.dumps(
                    {
                        "requestId": aws_apigateway.AccessLogField.context_request_id(),
                        "caller": aws_apigateway.AccessLogField.context_identity_caller(),
                        "httpMethod": aws_apigateway.AccessLogField.context_http_method(),
                        "ip": aws_apigateway.AccessLogField.context_identity_source_ip(),
                        "protocol": aws_apigateway.AccessLogField.context_protocol(),
                        "requestTime": aws_apigateway.AccessLogField.context_request_time(),
                        "resourcePath": aws_apigateway.AccessLogField.context_resource_path(),
                        "responseLength": aws_apigateway.AccessLogField.context_response_length(),
                        "status": aws_apigateway.AccessLogField.context_status(),
                        "user": aws_apigateway.AccessLogField.context_identity_user(),
                        "errorMessage": aws_apigateway.AccessLogField.context_error_message(),
                        "domainName": aws_apigateway.AccessLogField.context_domain_name(),
                        "vpcId": "$context.identity.vpcId",
                        "vpceId": "$context.identity.vpceId",
                    }
                )
            ),
            description=version_description,
            stage_name=api_version,
            method_options=method_options_to_disable_cache,
            throttling_rate_limit=1000,
            throttling_burst_limit=500,
        )

    def _configure_vpc_endpoint(self, endpoint_type, vpc_endpoint):
        if endpoint_type == aws_apigateway.EndpointType.PRIVATE and vpc_endpoint:
            self._api.node.default_child.add_property_override(
                "EndpointConfiguration.VpcEndpointIds", [vpc_endpoint.vpc_endpoint_id]
            )

    def _create_api_outputs(self, app_config, stack, name, waf_acl_arn):
        if waf_acl_arn:
            aws_wafv2.CfnWebACLAssociation(
                self, "WAFACLAssociation", web_acl_arn=waf_acl_arn, resource_arn=self._api.deployment_stage.stage_arn
            )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-ApiIdSsmParameter",
            parameter_name=f"/{app_config.format_resource_name(name)}/api/id",
            description=f"{app_config.component_name} API Id",
            string_value=self._api.rest_api_id,
        )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-ApiUrl",
            parameter_name=f"/{app_config.format_resource_name(name)}/api/url",
            description=f"{app_config.component_name} API url",
            string_value=self._api.url_for_path(),
        )

        aws_cdk.CfnOutput(self, "ApiUrlOutput", value=self._api.url_for_path(), description="Invoke URL of the API.")

    def _add_suppressions(self, access_log_group, api_role, cache_enabled, stack):
        self._add_log_group_suppressions(access_log_group)
        self._add_api_suppressions()
        self._add_role_policy_suppressions(api_role)
        self._add_stage_suppressions(cache_enabled)
        self._add_stack_suppressions(stack)

    def _add_log_group_suppressions(self, access_log_group):
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

    def _add_api_suppressions(self):
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._api,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG2",
                    reason="Request validation is enabled in OpenAPI schema.",
                ),
            ],
        )

    def _add_role_policy_suppressions(self, api_role):
        api_role_policy = [p for p in api_role.node.children if isinstance(p, aws_iam.Policy)][0]
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=api_role_policy,
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

    def _add_stage_suppressions(self, cache_enabled):
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

    def _add_stack_suppressions(self, stack):
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

    def __get_resource_policy(self, policy, vpc_endpoint, endpoint_type):
        return (
            policy
            if policy
            else (
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
                and vpc_endpoint  # Deny all if API gateway is private but no VPC endpoint is provided
                else (
                    aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.DENY,
                                principals=[aws_iam.AnyPrincipal()],
                                actions=["execute-api:Invoke"],
                                resources=[aws_cdk.Stack.of(self).format_arn(service="execute-api", resource="*")],
                            ),
                        ]
                    )
                    if endpoint_type == aws_apigateway.EndpointType.PRIVATE
                    else None
                )
            )
        )

    def __get_auth_arn(self, cedar_policy_config, app_config):
        if cedar_policy_config is None:
            return None

        return aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.format_ssm_parameter_name(
                component_name=constants.AUTH_BC_NAME,
                name=constants.AUTH_BC_HANDLER_PARAM_NAME,
            ),
        )

    def _create_iam_api(
        self,
        app_config,
        handler_arn,
        api_role,
        api_version,
        version_description,
        cache_enabled,
        waf_acl_arn,
        cache_explicit_disable,
        endpoint_type,
        vpc_endpoint,
        policy,
        stack,
        cedar_policy_config,
        iam_role_access,
    ):
        iam_schema_dict = self._prepare_iam_schema(
            handler_arn, api_role, app_config, cedar_policy_config, iam_role_access
        )
        iam_access_log_group = self._create_iam_log_group(app_config)

        method_options_to_disable_cache = {
            key: aws_apigateway.MethodDeploymentOptions(caching_enabled=False, cache_ttl=aws_cdk.Duration.seconds(0))
            for key in cache_explicit_disable
        }

        iam_api = aws_apigateway.SpecRestApi(
            self,
            "IAMApi",
            api_definition=aws_apigateway.ApiDefinition.from_inline(iam_schema_dict),
            deploy=True,
            deploy_options=self._create_stage_options(
                iam_access_log_group,
                api_version,
                f"{version_description} with IAM Auth",
                cache_enabled,
                method_options_to_disable_cache,
                app_config,
            ),
            endpoint_types=[endpoint_type],
            fail_on_warnings=True,
            policy=self.__get_resource_policy(policy, vpc_endpoint, endpoint_type),
            rest_api_name=app_config.format_resource_name("iam-api"),
        )

        if endpoint_type == aws_apigateway.EndpointType.PRIVATE and vpc_endpoint:
            iam_api.node.default_child.add_property_override(
                "EndpointConfiguration.VpcEndpointIds", [vpc_endpoint.vpc_endpoint_id]
            )

        self._create_iam_api_outputs(app_config, stack, waf_acl_arn, iam_api)
        self._add_iam_api_suppressions(iam_access_log_group, iam_api, cache_enabled)
        return iam_api

    def _prepare_iam_schema(self, handler_arn, api_role, app_config, cedar_policy_config, iam_role_access):
        iam_schema_dict = yaml.safe_load(
            self.template.render(
                handler_arn=handler_arn,
                apigw_invocation_role_arn=api_role.role_arn,
                cors_origin=f"'{app_config.environment_config['rest-api-cors-origins']}'",
            )
        )

        if iam_role_access:
            iam_schema_dict = self._filter_schema_by_role(iam_schema_dict, cedar_policy_config, iam_role_access)

        if "components" not in iam_schema_dict:
            iam_schema_dict["components"] = {}
        iam_schema_dict["components"]["securitySchemes"] = {
            "sigv4": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "x-amazon-apigateway-authtype": "awsSigv4",
            }
        }

        self._remove_authorization_from_schema(iam_schema_dict)
        self._validate_schema_auth(iam_schema_dict, "IAM API", no_auth_paths=[])
        return iam_schema_dict

    def _remove_authorization_from_schema(self, schema_dict):
        for path_data in schema_dict.get("paths", {}).values():
            for method_data in path_data.values():
                if isinstance(method_data, dict):
                    if "security" in method_data:
                        method_data["security"] = [{"sigv4": []}]
                    if "parameters" in method_data:
                        method_data["parameters"] = [
                            p
                            for p in method_data["parameters"]
                            if not (isinstance(p, dict) and p.get("name") == "Authorization")
                        ]
                    if "x-amazon-apigateway-integration" in method_data:
                        integration = method_data["x-amazon-apigateway-integration"]
                        if "cacheKeyParameters" in integration:
                            integration["cacheKeyParameters"] = [
                                p for p in integration["cacheKeyParameters"] if "Authorization" not in p
                            ]

    def _validate_schema_auth(self, schema_dict, api_name, no_auth_paths=None):
        no_auth_paths = no_auth_paths or []
        security_schemes = set(schema_dict.get("components", {}).get("securitySchemes", {}).keys())

        default_security_schemes = schema_dict.get("security", [])

        methods_wo_auth = self._find_methods_without_auth(
            schema_dict, security_schemes, no_auth_paths, default_security_schemes
        )
        if methods_wo_auth:
            raise ValueError(f"{api_name} schema validation failed: Methods without auth detected: {methods_wo_auth}")

    def _find_methods_without_auth(self, schema_dict, security_schemes, no_auth_paths, default_security_schemes):
        methods_wo_auth = {}
        for path, path_data in schema_dict.get("paths", {}).items():
            if path in no_auth_paths:
                continue
            for method, method_data in path_data.items():
                if isinstance(method_data, dict) and method != "options":
                    auth = method_data.get("security", [])
                    if not default_security_schemes and (
                        not auth or not {a for aa in auth for a in aa.keys()}.issubset(security_schemes)
                    ):
                        if path not in methods_wo_auth:
                            methods_wo_auth[path] = []
                        methods_wo_auth[path].append(method)
        return methods_wo_auth

    def _filter_schema_by_role(self, schema_dict, cedar_policy_config, iam_role_access):
        action_to_roles = self._build_action_role_mapping(cedar_policy_config)
        filtered_paths = {}

        for path, path_data in schema_dict.get("paths", {}).items():
            filtered_methods = {}
            for method, method_data in path_data.items():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    operation_id = method_data["operationId"]
                    allowed_roles = action_to_roles.get(operation_id, set())
                    if not allowed_roles or iam_role_access in allowed_roles:
                        filtered_methods[method] = method_data
                else:
                    filtered_methods[method] = method_data
            if filtered_methods:
                filtered_paths[path] = filtered_methods

        schema_dict["paths"] = filtered_paths
        return schema_dict

    def _build_action_role_mapping(self, cedar_policy_config):
        action_to_roles = {}
        for policy in cedar_policy_config.cedar_policies:
            roles = self._extract_roles_from_policy(policy.statement)
            actions = self._extract_actions_from_policy(policy.statement)
            for action in actions:
                if action not in action_to_roles:
                    action_to_roles[action] = set()
                action_to_roles[action].update(roles)
        return action_to_roles

    def _extract_roles_from_policy(self, statement):
        roles = set()
        for pattern, role in config.CEDAR_RESOURCE_TO_ROLE_MAPPING.items():
            if pattern in statement:
                roles.add(role)
        return roles

    def _extract_actions_from_policy(self, statement):
        actions = set()
        matches = re.findall(r'Action::"([^"]+)"', statement)
        actions.update(matches)
        return actions

    def _create_iam_log_group(self, app_config, encryption_key=None):
        return aws_logs.LogGroup(
            self,
            "BackendAppIAMApiAccessLogGroup",
            log_group_name=app_config.format_resource_name("iam-api-access-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
            encryption_key=encryption_key,
        )

    def _create_iam_api_outputs(self, app_config, stack, waf_acl_arn, iam_api):
        if waf_acl_arn:
            aws_wafv2.CfnWebACLAssociation(
                self, "IAMWAFACLAssociation", web_acl_arn=waf_acl_arn, resource_arn=iam_api.deployment_stage.stage_arn
            )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-IAMApiIdSsmParameter",
            parameter_name=f"/{app_config.format_resource_name('iam-api')}/api/id",
            description=f"{app_config.component_name} IAM API Id",
            string_value=iam_api.rest_api_id,
        )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-IAMApiUrl",
            parameter_name=f"/{app_config.format_resource_name('iam-api')}/api/url",
            description=f"{app_config.component_name} IAM API url",
            string_value=iam_api.url_for_path(),
        )

        aws_ssm.StringParameter(
            self,
            f"{stack.stack_name}-IAMApiArnSsmParameter",
            parameter_name=f"/{app_config.format_resource_name('iam-api')}/api/arn",
            description=f"{app_config.component_name} IAM API ARN",
            string_value=iam_api.arn_for_execute_api(),
        )

        aws_cdk.CfnOutput(
            self, "IAMApiUrlOutput", value=iam_api.url_for_path(), description="Invoke URL of the IAM API."
        )

    def _add_iam_api_suppressions(self, iam_access_log_group, iam_api, cache_enabled):
        self._add_log_group_suppressions(iam_access_log_group)

        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=iam_api,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG2",
                    reason="Request validation is enabled in OpenAPI schema.",
                ),
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=iam_api.deployment_stage,
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
                construct=iam_api.deployment_stage,
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

    @property
    def api(self) -> aws_apigateway.SpecRestApi:
        return self._api

    @property
    def iam_api(self) -> typing.Optional[aws_apigateway.SpecRestApi]:
        return self._iam_api
