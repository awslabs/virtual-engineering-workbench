import enum
import json

import constructs
import pydantic
from aws_cdk import aws_apigateway, aws_iam, aws_ssm, aws_verifiedpermissions

from infra import config, constants


class AuthFeature(enum.StrEnum):
    # Checks for a user role in a project assignment
    ProjectAssignments = "ProjectAssignments"


class CedarPolicy(pydantic.BaseModel):
    description: str = pydantic.Field(...)
    statement: str = pydantic.Field(...)


class CedarPolicyConfig(pydantic.BaseModel):
    cedar_schema: dict = pydantic.Field(...)
    cedar_policies: list[CedarPolicy] = pydantic.Field(...)
    entity_resolution_apis: list[str] = pydantic.Field([])
    # Defaults to the authorization using project assignments
    auth_features: list[AuthFeature] = pydantic.Field([AuthFeature.ProjectAssignments])


class BackendAppAPIAuth(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        api: aws_apigateway.RestApiBase,
        cedar_config: CedarPolicyConfig | None = None,
    ) -> None:
        super().__init__(scope, id)

        if not cedar_config:
            return

        if cedar_config.entity_resolution_apis:
            authorization_bc_handler_role_arn = aws_ssm.StringParameter.value_for_string_parameter(
                self,
                app_config.format_ssm_parameter_name(
                    component_name=constants.AUTH_BC_NAME,
                    name=constants.AUTH_BC_HANDLER_ROLE_PARAM_NAME,
                ),
            )

            aws_iam.ManagedPolicy(
                self,
                "AuthorizerPolicy",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=["execute-api:Invoke"],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            api.arn_for_execute_api(
                                method="GET",
                                path=path,
                                stage=api.deployment_stage.stage_name,
                            )
                            for path in cedar_config.entity_resolution_apis
                        ],
                    )
                ],
                managed_policy_name=app_config.format_resource_name("authorizer-policy"),
                roles=[aws_iam.Role.from_role_arn(self, "AuthorizerLambdaRole", authorization_bc_handler_role_arn)],
            )

        policy_store = aws_verifiedpermissions.CfnPolicyStore(
            self,
            "PolicyStore",
            description=f"Policy Store for {app_config.component_name} bounded context.",
            validation_settings={"mode": "STRICT"},
            schema=aws_verifiedpermissions.CfnPolicyStore.SchemaDefinitionProperty(
                cedar_json=json.dumps(cedar_config.cedar_schema)
            ),
        )

        aws_ssm.StringParameter(
            self,
            "PolicyStoreId",
            parameter_name=app_config.format_ssm_parameter_name(
                constants.AUTH_BC_POLICY_STORE_SSM_PARAM.format(bc_name=app_config.component_name),
                component_name=constants.AUTH_BC_NAME,
            ),
            string_value=json.dumps(
                {
                    "api_id": api.rest_api_id,
                    "api_url": api.url_for_path(),
                    "policy_store_id": policy_store.attr_policy_store_id,
                    "bounded_context": app_config.component_name,
                    "auth_features": cedar_config.auth_features,
                }
            ),
            description="Shared Policy Store ID for Verified Permissions",
        )

        for idx, cedar_policy in enumerate(cedar_config.cedar_policies):
            aws_verifiedpermissions.CfnPolicy(
                self,
                f"Policy-{idx}",
                definition=aws_verifiedpermissions.CfnPolicy.PolicyDefinitionProperty(
                    static=aws_verifiedpermissions.CfnPolicy.StaticPolicyDefinitionProperty(
                        statement=cedar_policy.statement,
                        description=cedar_policy.description,
                    ),
                ),
                policy_store_id=policy_store.attr_policy_store_id,
            )
