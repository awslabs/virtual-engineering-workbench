import typing

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_ec2, aws_iam, aws_logs, aws_ssm

from infra import config
from infra.constructs import backend_app_openapi


class SecurityStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        apis: typing.List[backend_app_openapi.BackendAppOpenApi],
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # CloudWatch resource policy to allow EventBridge event logging
        aws_logs.ResourcePolicy(
            self,
            "event-bridge-resource-policy",
            policy_statements=[
                aws_iam.PolicyStatement(
                    principals=[aws_iam.ServicePrincipal("events.amazonaws.com")],
                    actions=["logs:PutLogEvents", "logs:CreateLogStream"],
                    resources=[
                        aws_cdk.Stack.of(self).format_arn(
                            service="logs",
                            resource="log-group",
                            arn_format=aws_cdk.ArnFormat.COLON_RESOURCE_NAME,
                            resource_name="".join(
                                ["/events/", app_config.format_resource_name_with_component("*", "events"), ":*"]
                            ),
                        )
                    ],
                )
            ],
            resource_policy_name=app_config.format_resource_name("allow-event-bridge-log"),
        )

        # VPC Endpoints
        vpc_name = app_config.environment_config["vpc-name"]
        if vpc_name:
            vpc = aws_ec2.Vpc.from_lookup(self, "vpc", vpc_name=vpc_name)
            vpc.add_gateway_endpoint("ddb-gateway-endpoint", service=aws_ec2.GatewayVpcEndpointAwsService.DYNAMODB)

        # IAM Role for technical VEW API access
        if app_config.environment_config["tools-account-id-ssm-param"]:
            account_on_boarding_account = aws_ssm.StringParameter.from_string_parameter_name(
                self,
                "account_on_boarding_account",
                string_parameter_name=app_config.environment_config["tools-account-id-ssm-param"].format(
                    environment=app_config.environment
                ),
            ).string_value

            api_arns = [api.api.arn_for_execute_api(path="/internal/*") for api in apis]

            managed_policy = aws_iam.ManagedPolicy(
                self,
                "api-access-policy",
                managed_policy_name="VEWWebAppApiAccessRolePolicy",
                description="Grants permissions to invoke VEW APIs.",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=["execute-api:Invoke"], effect=aws_iam.Effect.ALLOW, resources=api_arns
                    )
                ],
            )

            execution_role_composite_policy = aws_iam.CompositePrincipal(
                aws_iam.AccountPrincipal(account_on_boarding_account),
            )

            execution_role = aws_iam.Role(
                self,
                "api-access-role",
                role_name="VEWWebAppApiAccessRole",
                managed_policies=[managed_policy],
                assumed_by=execution_role_composite_policy,
                description="VEW components on different accounts use this role to invoke VEW API using IAM auth.",
            )

            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=managed_policy,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="This policy grants invoke action to all API endpoints.",
                    ),
                ],
            )

            aws_cdk.CfnOutput(
                self,
                "VEWApiAccessRoleArn",
                value=execution_role.role_arn,
                description="Role to invoke VEW apis.",
            )
