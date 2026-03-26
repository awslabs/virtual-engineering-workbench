import typing

import cdk_nag
import constructs
from aws_cdk import Duration, Stack, aws_iam, aws_ssm, custom_resources

from infra.constructs import backend_app_function

EB_UPSERT_SSM_PARAM_NAME = "/virtual-workbench/{environment}/custom-resource/be-eb-upsert"


class EBUpsert(constructs.Construct):

    def __init__(
        self,
        scope: constructs.Construct,
        construct_id: str,
        format_resource_name: typing.Callable[[str], str],
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region

        lambda_managed_policy = aws_iam.ManagedPolicy(
            self,
            "eb-upsert-policy",
            managed_policy_name=format_resource_name(f"eb-upsert-{region}"),
            description="Grants permission to read and create EventBus for a custom CF resource..",
            path="/VirtualWorkbench/",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "events:DescribeEventBus",
                        "events:CreateEventBus",
                    ],
                    resources=["*"],
                )
            ],
        )

        func = backend_app_function.BackendAppFunction(
            self,
            "handler",
            app_root="infra",
            entry="infra/eb_upsert_handler",
            lambda_root="infra/constructs/eventbridge/eb_upsert_handler",
            layers=[],
            function_name=format_resource_name("eb-upsert"),
            reserved_concurrency=10,
            provisioned_concurrency=None,
            timeout=Duration.seconds(15),
            memory_size=256,
            permissions=[
                lambda f: f.role.add_managed_policy(lambda_managed_policy),
                lambda f: f.role.add_managed_policy(
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ),
            ],
        )

        service_provider_role = aws_iam.Role(
            self,
            "service-provider-role",
            role_name=format_resource_name(f"service-provider-role-{region}"),
            path="/VirtualWorkbench/",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        eb_upsert_provider = custom_resources.Provider(
            self,
            "eb-upsert-provider",
            on_event_handler=func.function,
            role=service_provider_role,
        )

        aws_ssm.StringParameter(
            self,
            "eb-upsert-service-ssm",
            parameter_name=EB_UPSERT_SSM_PARAM_NAME.format(environment=environment),
            string_value=eb_upsert_provider.service_token,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            lambda_managed_policy,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs to create or read arbitrary event bridges.",
                ),
            ],
            apply_to_children=True,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            func.function,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Lambda is using a default Lambda execution role policy for CloudWatch access.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-LambdaInsideVPC",
                    reason="Lambdas are not deployed to VPC.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaDLQ",
                    reason="Lambda is synchronous and does not require DLQ.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaInsideVPC",
                    reason="Lambdas are not deployed to VPC.",
                ),
            ],
            apply_to_children=True,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            service_provider_role,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Lambda is using a default Lambda execution role policy for CloudWatch access.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs to create or read arbitrary event bridge event buses.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Role has no inline policies defined.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Role has no inline policies defined.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Role has no inline policies defined.",
                ),
            ],
            apply_to_children=True,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            eb_upsert_provider,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Lambda is using a default Lambda execution role policy for CloudWatch access.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-LambdaInsideVPC",
                    reason="Lambdas are not deployed to VPC.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-LambdaInsideVPC",
                    reason="Lambdas are not deployed to VPC.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaDLQ",
                    reason="Lambda is triggeted by a schedule and does not need a DLQ.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaInsideVPC",
                    reason="Lambdas are not deployed to VPC.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Function needs to create or read arbitrary event bridges.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Code is autogenerated by CDK and does not support latest Node.js runtime.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaConcurrency",
                    reason="Code is autogenerated by CDK and does not configure reserved concurrency.",
                ),
            ],
            apply_to_children=True,
        )
