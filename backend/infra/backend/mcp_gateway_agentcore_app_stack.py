"""AgentCore-based MCP gateway.

One Amazon Bedrock AgentCore Gateway that aggregates one OpenAPI target per
enabled bounded context. Inbound auth validates only the issuer + OIDC client
(CUSTOM_JWT); a REQUEST interceptor Lambda forwards the caller's bearer token so
the bounded context's existing shared authorizer performs the real authorization.

There is deliberately NO RESPONSE interceptor. One was tried to surface upstream
error detail and could not: for an MCP tool call the gateway has already collapsed
the target's HTTP response into a JSON-RPC body (always transport 200, the failure
carried as ``result.isError``) before a RESPONSE interceptor runs, so there is
nothing left for it to recover. ``exceptionLevel=DEBUG`` on the gateway is the
mechanism that surfaces granular messages; see ``gateway-exception-level`` below.

The published OpenAPI spec each target consumes is produced at CDK synth by
``infra.helpers.mcp_openapi_transform`` and uploaded via ``BucketDeployment``
(``Source.json_data``); there is no publisher Lambda. This stack is a pure sink —
it depends on the bounded-context API stacks (and the api-integration stack when
custom DNS is on) so it deploys last, and it does NOT add a reverse edge from the
authorization stack (which consumes the OIDC-client audience at runtime).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os

import aws_cdk
import cdk_nag
import constructs
import yaml
from aws_cdk import aws_bedrockagentcore, aws_iam, aws_logs
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_ssm, aws_wafv2

from infra import config, constants
from infra.backend import vew_bounded_context_stack
from infra.constructs import backend_app_function
from infra.constructs.kms import key as kms_key
from infra.constructs.s3 import bucket as s3_bucket
from infra.helpers import mcp_openapi_transform

# AgentCore caps the gateway's MCP `instructions` at 2048 chars (enforced by CloudFormation).
_MAX_INSTRUCTIONS_LEN = 2048


def build_target_specs(source_specs: dict[str, dict], base_urls: dict[str, str]) -> dict[str, dict]:
    """Build and validate the exact transformed schemas uploaded by the gateway."""
    published = {
        context: mcp_openapi_transform.transform(source_spec, base_urls[context])
        for context, source_spec in source_specs.items()
    }
    mcp_openapi_transform.validate_target_specs(published)
    return published


class McpGatewayAgentcoreStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        enabled_stacks: list[vew_bounded_context_stack.VEWBoundedContextStack],
        custom_domain: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self._app_config = app_config
        self._custom_domain = custom_domain

        # Deploy last: depend on every consumed bounded-context stack.
        for stack in enabled_stacks:
            self.add_dependency(stack)

        # OIDC client on the existing user pool
        # The client is created by the frontend stack from its AdditionalAppClients
        # config, which publishes one SSM parameter per client. This stack reads
        # that parameter rather than creating a client of its own, so the
        # authorizer's accepted-client list stays the single mechanism it already
        # is. Register the gateway by adding an "mcp-gateway-agentcore" entry to
        # AdditionalAppClients with the callback URLs in
        # constants.MCP_GATEWAY_OAUTH_REDIRECT_URIS.
        mcp_client_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-mcp-gateway-client-id-ssm-param"].format(
                environment=app_config.environment
            ),
        )

        user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=app_config.environment),
        )
        cognito_region = app_config.environment_config["cognito-region"]
        discovery_url = (
            f"https://cognito-idp.{cognito_region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
        )

        # Gateway identity, fixed up front
        # The gateway's own ARN is only known after CfnGateway is created, but the role it
        # assumes has to exist first. Both the role trust policy and the interceptor's
        # resource policy therefore condition on an ARN *pattern* built from the gateway's
        # name, which is deterministic. AgentCore documents the gateway ARN as
        # ...:gateway/([0-9a-z][-]?){1,48}-[a-z0-9]{10} (GetGateway API reference), i.e. the
        # name followed by a generated 10-character suffix - hence the trailing wildcard.
        gateway_name = app_config.format_resource_name("gw", max_length=48)
        gateway_arn_pattern = self.format_arn(
            service="bedrock-agentcore",
            resource="gateway",
            resource_name=f"{gateway_name}-*",
            arn_format=aws_cdk.ArnFormat.SLASH_RESOURCE_NAME,
        )

        # Gateway service role: invoke the interceptors + read the spec bucket. No execute-api:Invoke.
        # The service principal is confused-deputy bait without source conditions: without
        # them any AgentCore gateway in any account could have the service assume this role.
        gateway_role = aws_iam.Role(
            self,
            "GatewayRole",
            role_name=app_config.format_resource_name("gw-role"),
            assumed_by=aws_iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.account},
                    "ArnLike": {"aws:SourceArn": gateway_arn_pattern},
                },
            ),
        )

        # REQUEST interceptor Lambda: forwards the caller's Authorization header
        #     (stdlib only, no layer)
        interceptor = self._build_interceptor(
            construct_id="Interceptor",
            entry_name="interceptor",
            function_name="interceptor",
            app_config=app_config,
            gateway_role=gateway_role,
            gateway_arn_pattern=gateway_arn_pattern,
        )

        # Spec bucket + synth-time transform → BucketDeployment
        # Bucket names are GLOBAL. Rely on the shared construct's default
        # account+region suffixing (the VEW house standard — 5 of 7 call sites) so this
        # stack can be deployed in more than one account. Previously this set
        # force_bucket_name_uniqueness=False with nothing compensating, so the second
        # account to deploy MCP anywhere in the partition failed with
        # "bucket already exists".
        # max_length=34 leaves room for the construct's "-<12-digit account>-<region>"
        # suffix (28 chars for a 14-char region such as ap-southeast-4) inside S3's
        # 63-char limit, with margin. format_resource_name truncates and appends a
        # 5-char hash when it has to.
        spec_bucket = s3_bucket.Bucket(
            self,
            "SpecBucket",
            bucket_name=app_config.format_resource_name(constants.MCP_AGENTCORE_SPEC_BUCKET_NAME, max_length=34),
            versioned=True,
            auto_delete_objects=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )
        bucket = spec_bucket.bucket
        bucket.grant_read(gateway_role)

        # Content-addressed spec keys: the S3 key (and thus the target's schema URI)
        # embeds a hash of the published spec, so an API change moves the target to a
        # new URI on deploy -> CloudFormation updates the target -> AgentCore re-reads
        # the schema and regenerates tools. (Overwriting a stable key would not: the
        # target's properties would be unchanged and AgentCore would not re-sync.)
        spec_keys: dict[str, str] = {}
        spec_deployment = None
        instruction_blocks: list[str] = []
        if enabled_stacks:
            sources = []
            source_specs = {
                stack.bounded_context: self._load_source_spec(stack.bounded_context) for stack in enabled_stacks
            }
            base_urls = {stack.bounded_context: self._resolve_base_url(stack) for stack in enabled_stacks}
            published_specs = build_target_specs(source_specs, base_urls)

            for stack in enabled_stacks:
                context = stack.bounded_context
                source_spec = source_specs[context]
                published = published_specs[context]
                digest = hashlib.sha256(json.dumps(published, sort_keys=True, default=str).encode()).hexdigest()[:12]
                key = f"{context}-{digest}.json"
                spec_keys[context] = key
                sources.append(s3deploy.Source.json_data(key, published))

                # Gateway instructions: each BC's OpenAPI info.description (verbatim, generic BC-level
                # context only — operation-specific detail lives in each operation's description so it
                # reaches the tool doc), XML-wrapped so the agent can tell which BC it belongs to.
                description = (source_spec.get("info") or {}).get("description")
                if description:
                    instruction_blocks.append(f'<context name="{context}">\n{description.strip()}\n</context>')
            spec_deployment = s3deploy.BucketDeployment(
                self,
                "SpecDeployment",
                destination_bucket=bucket,
                sources=sources,
            )
        instructions = "\n\n".join(instruction_blocks) or None
        if instructions and len(instructions) > _MAX_INSTRUCTIONS_LEN:
            raise ValueError(
                f"MCP gateway instructions are {len(instructions)} chars, over the "
                f"{_MAX_INSTRUCTIONS_LEN}-char limit; shorten the bounded contexts' x-summary."
            )

        # Gateway (CUSTOM_JWT inbound + REQUEST interceptor)
        gateway = aws_bedrockagentcore.CfnGateway(
            self,
            "Gateway",
            name=gateway_name,
            role_arn=gateway_role.role_arn,
            protocol_type="MCP",
            protocol_configuration=(
                aws_bedrockagentcore.CfnGateway.GatewayProtocolConfigurationProperty(
                    mcp=aws_bedrockagentcore.CfnGateway.MCPGatewayConfigurationProperty(instructions=instructions)
                )
                if instructions
                else None
            ),
            # DEBUG returns granular exception messages instead of the gateway's generic
            # "An internal error occurred. Please retry later.", which otherwise hides the
            # target's own 4xx message (the bounded context APIs already return the real
            # text - handle_exceptions maps a DomainException to 400 with str(e)).
            # Configured per environment because it exposes internals to any authenticated
            # caller, so it must never be on in prod.
            exception_level=app_config.component_specific.get("gateway-exception-level"),
            authorizer_type="CUSTOM_JWT",
            authorizer_configuration=aws_bedrockagentcore.CfnGateway.AuthorizerConfigurationProperty(
                custom_jwt_authorizer=aws_bedrockagentcore.CfnGateway.CustomJWTAuthorizerConfigurationProperty(
                    discovery_url=discovery_url,
                    allowed_clients=[mcp_client_id],
                )
            ),
            interceptor_configurations=[
                aws_bedrockagentcore.CfnGateway.GatewayInterceptorConfigurationProperty(
                    interception_points=["REQUEST"],
                    interceptor=aws_bedrockagentcore.CfnGateway.InterceptorConfigurationProperty(
                        lambda_=aws_bedrockagentcore.CfnGateway.LambdaInterceptorConfigurationProperty(
                            arn=interceptor.function_alias.function_arn,
                        )
                    ),
                    input_configuration=aws_bedrockagentcore.CfnGateway.InterceptorInputConfigurationProperty(
                        pass_request_headers=True,
                    ),
                ),
            ],
        )

        # One OpenAPI target per enabled context (no-auth outbound; JWT forwarded by interceptor)
        for stack in enabled_stacks:
            ctx = stack.bounded_context
            target = aws_bedrockagentcore.CfnGatewayTarget(
                self,
                f"Target{app_config.format_to_pascal_case(ctx)}",
                name=ctx,
                gateway_identifier=gateway.attr_gateway_identifier,
                target_configuration=aws_bedrockagentcore.CfnGatewayTarget.TargetConfigurationProperty(
                    mcp=aws_bedrockagentcore.CfnGatewayTarget.McpTargetConfigurationProperty(
                        open_api_schema=aws_bedrockagentcore.CfnGatewayTarget.ApiSchemaConfigurationProperty(
                            s3=aws_bedrockagentcore.CfnGatewayTarget.S3ConfigurationProperty(
                                uri=bucket.s3_url_for_object(spec_keys[ctx]),
                                bucket_owner_account_id=app_config.account,
                            )
                        )
                    )
                ),
                # No-auth outbound: `credential_provider_configurations` is omitted so the
                # interceptor-forwarded JWT is the only Authorization the backend receives
            )
            target.add_dependency(gateway)
            if spec_deployment is not None:
                target.node.add_dependency(spec_deployment)

        self._gateway = gateway

        # WAF: reuse the same regional Web ACL the bounded-context APIs use
        # AgentCore Gateway is a WAF-associable resource type; associate the shared regional
        # API Web ACL (the one every BC API stack reads from the same SSM param) so the MCP
        # endpoint gets identical edge protection. The ACL and gateway are both regional.
        api_acl_arn = aws_ssm.StringParameter.from_string_parameter_attributes(
            self,
            "WafApiAclArnRegional",
            parameter_name=constants.WAF_API_ACL_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value
        waf_association = aws_wafv2.CfnWebACLAssociation(
            self,
            "GatewayWafAssociation",
            web_acl_arn=api_acl_arn,
            resource_arn=gateway.attr_gateway_arn,
        )
        waf_association.add_dependency(gateway)

        # Observability: deliver gateway APPLICATION_LOGS to CloudWatch
        # AgentCore has no logging property on the gateway; logs are wired via the standard
        # CloudWatch log-delivery mechanism. APPLICATION_LOGS carry request/response bodies and
        # target (backend) error messages — the surface that explains a tools/call failure.
        # These logs can hold user data from the bounded-context APIs, so encrypt them with a
        # customer-managed key (rotation on), like VEW's other log groups. The key gets its own
        # alias because the log-group name starts with /aws/, a reserved alias prefix.
        gateway_logs_key = kms_key.Key(
            self,
            "GatewayLogsKey",
            alias=app_config.format_resource_name("gw-logs-key"),
            description="Key used to encrypt/decrypt the MCP gateway application logs.",
        )
        # Keep the construct id "GatewayLogs" directly on the LogGroup: its logical id must stay
        # GatewayLogs64F6314F so existing deployments update the group in place (adding the KMS
        # key) instead of replacing it. A replacement creates the new group first and fails,
        # because the physical name is unchanged and still held by the old one.
        gateway_log_group_name = f"/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/{gateway.ref}"
        gateway_log_group = aws_logs.LogGroup(
            self,
            "GatewayLogs",
            log_group_name=gateway_log_group_name,
            encryption_key=gateway_logs_key.key,
            retention=aws_logs.RetentionDays.ONE_MONTH,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )
        # Let CloudWatch Logs use the key for this log group only. The Logs principal in a key
        # policy is REGIONAL (logs.<region>.<url suffix>): the service principal has to be in the
        # same Region as the key, so the global form never matches and ingestion into the
        # encrypted group fails. See "Encrypt log data in CloudWatch Logs using AWS KMS".
        gateway_logs_key.key.grant_encrypt_decrypt(
            aws_iam.ServicePrincipal(
                f"logs.{self.region}.{self.url_suffix}",
                conditions={
                    "ArnEquals": {
                        "kms:EncryptionContext:aws:logs:arn": self.format_arn(
                            service="logs",
                            resource="log-group",
                            resource_name=gateway_log_group_name,
                            arn_format=aws_cdk.ArnFormat.COLON_RESOURCE_NAME,
                        ),
                    },
                },
            )
        )
        log_source = aws_logs.CfnDeliverySource(
            self,
            "GatewayLogSource",
            name=app_config.format_resource_name("gw-logs-src", max_length=60),
            log_type="APPLICATION_LOGS",
            resource_arn=gateway.attr_gateway_arn,
        )
        log_destination = aws_logs.CfnDeliveryDestination(
            self,
            "GatewayLogDestination",
            name=app_config.format_resource_name("gw-logs-dest", max_length=60),
            destination_resource_arn=gateway_log_group.log_group_arn,
        )
        log_delivery = aws_logs.CfnDelivery(
            self,
            "GatewayLogDelivery",
            delivery_source_name=log_source.name,
            delivery_destination_arn=log_destination.attr_arn,
        )
        log_delivery.add_dependency(log_source)
        log_delivery.add_dependency(log_destination)

        # Output the MCP endpoint for the client config / docs
        aws_cdk.CfnOutput(self, "GatewayUrl", value=gateway.attr_gateway_url)
        aws_cdk.CfnOutput(self, "GatewayLogGroup", value=gateway_log_group.log_group_name)
        aws_ssm.StringParameter(
            self,
            "GatewayUrlParam",
            parameter_name=app_config.format_ssm_parameter_name("gateway-url"),
            string_value=gateway.attr_gateway_url,
        )

        # Ready-to-paste client configs (server name = org-app-env, e.g. proserve-wb-dev)
        server_name = (
            f"{app_config.get_organization_prefix()}-{app_config.get_application_prefix()}-{app_config.environment}"
        )
        client_id = mcp_client_id
        callback_port = constants.MCP_GATEWAY_OAUTH_CALLBACK_PORT
        gateway_url = gateway.attr_gateway_url

        aws_cdk.CfnOutput(
            self,
            "ClaudeMcpConfig",
            description="Run this to register the MCP server with Claude CLI.",
            value=(
                f"claude mcp add --transport http --scope local "
                f"--client-id {client_id} --callback-port {callback_port} "
                f"{server_name} {gateway_url}"
            ),
        )
        aws_cdk.CfnOutput(
            self,
            "KiroMcpConfig",
            description="Add this entry to kiro-cli mcpServers config.",
            value=(
                f'"{server_name}" : {{\n'
                f'  "url" : "{gateway_url}",\n'
                f'  "oauth" : {{\n'
                f'    "clientId" : "{client_id}",\n'
                f'    "redirectUri" : "http://localhost:{callback_port}",\n'
                f'    "oauthScopes" : [ "openid", "email", "profile" ]\n'
                f"  }}\n"
                f"}}"
            ),
        )

        self._suppress_nag(gateway_role, spec_deployment)

    # ------------------------------------------------------------------ helpers

    def _build_interceptor(
        self,
        construct_id: str,
        entry_name: str,
        function_name: str,
        app_config: config.AppConfig,
        gateway_role: aws_iam.Role,
        gateway_arn_pattern: str,
    ) -> backend_app_function.BackendAppFunction:
        """Create one interceptor Lambda and let the gateway invoke it.

        Both interceptors are stdlib-only, so they take no layer. The gateway needs
        the grant on both the role it assumes and the service principal.
        """
        interceptor = backend_app_function.BackendAppFunction(
            self,
            construct_id,
            app_root="app",
            entry=f"app/mcp_gateway_agentcore/entrypoints/{entry_name}",
            lambda_root="app/mcp_gateway_agentcore",
            layers=[],
            function_name=app_config.format_resource_name(function_name),
            timeout=aws_cdk.Duration.seconds(15),
            memory_size=256,
            reserved_concurrency=app_config.component_specific["interceptor-reserved-concurrency"],
            permissions=[
                lambda f: f.role.add_managed_policy(
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ),
            ],
        )
        interceptor.function_alias.grant_invoke(gateway_role)
        # Same confused-deputy gap as the role trust policy: a bare service-principal
        # invoke permission lets any AgentCore gateway in any account invoke this Lambda.
        # add_permission (not grant_invoke) so SourceAccount/SourceArn are set.
        interceptor.function_alias.add_permission(
            "GatewayInvoke",
            principal=aws_iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=self.account,
            source_arn=gateway_arn_pattern,
        )
        return interceptor

    def _resolve_base_url(self, stack: vew_bounded_context_stack.VEWBoundedContextStack) -> str:
        """Base_Url for a context, resolved at synth.

        Custom DNS on: the shared custom domain + the context's base path (which
        equals ``stack.bounded_context`` for the exposed contexts, matching the
        ``CUSTOM_DNS_API_PATH_*`` constants). Off: the context's plain-string
        ``.../api/url`` SSM param (execute-api URL) as a deploy-time token.
        """
        if self._custom_domain:
            return f"https://{self._custom_domain}/{stack.bounded_context}"
        api = stack.api
        if api is None:
            raise ValueError(f"Context '{stack.bounded_context}' has no API to resolve a base URL from")
        return aws_ssm.StringParameter.value_for_string_parameter(self, api.api_url_ssm_parameter_name)

    @staticmethod
    def _load_source_spec(ctx: str) -> dict:
        """Read a bounded context's OpenAPI schema from the repo at synth."""
        module = ctx.replace("-", "_")
        schema_dir = os.path.join("app", module, "entrypoints", "api", "schema")
        matches = sorted(glob.glob(os.path.join(schema_dir, "*.yaml")))
        if not matches:
            raise FileNotFoundError(f"No OpenAPI schema for context '{ctx}' in {schema_dir}")
        with open(matches[0], "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _suppress_nag(self, gateway_role: aws_iam.Role, spec_deployment) -> None:
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=gateway_role,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Gateway role reads any object under the spec bucket and invokes the interceptor alias.",
                ),
            ],
            apply_to_children=True,
        )

        # The BucketDeployment Lambda + its (stack-level singleton) role are generated and managed
        # by CDK. Suppress on its handler_role like the existing product_publishing BucketDeployment.
        if spec_deployment is not None:
            handler_role = spec_deployment.handler_role
            role_policy = [c for c in handler_role.node.children if isinstance(c, aws_iam.Policy)][0]
            cdk_nag.NagSuppressions.add_resource_suppressions(
                handler_role.node.children,
                [
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM4",
                        reason="Autogenerated by CDK BucketDeployment.",
                    )
                ],
            )
            cdk_nag.NagSuppressions.add_resource_suppressions(
                role_policy,
                [
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="Autogenerated by CDK BucketDeployment.",
                    )
                ],
            )

        # Stack-wide: the CDK-managed BucketDeployment Lambda triggers these; inline policies are
        # acceptable here. Mirrors the suppressions on the existing product_publishing BucketDeployment.
        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=self,
            suppressions=[
                cdk_nag.NagPackSuppression(id="AwsSolutions-L1", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(id="NIST.800.53.R4-LambdaInsideVPC", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(id="NIST.800.53.R5-LambdaInsideVPC", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(id="PCI.DSS.321-LambdaInsideVPC", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaConcurrency",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(id="NIST.800.53.R5-LambdaDLQ", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(id="PCI.DSS.321-IAMNoInlinePolicy", reason="Autogenerated by CDK."),
            ],
        )
