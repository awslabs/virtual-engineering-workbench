import hashlib

import cdk_nag
import constructs
from aws_cdk import (
    ArnFormat,
    CustomResource,
    Duration,
    Stack,
    aws_iam,
    aws_ssm,
    custom_resources,
)

from infra.constructs import backend_app_function


class BackendAppImportedSSMParameters(constructs.Construct):
    """Reads SSM parameters that are shared with the spoke account."""

    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        name: str,
        auto_accept_invitations: bool = False,
    ):
        super().__init__(scope, id)

        if not auto_accept_invitations:
            # No need to accept invitations when sharing within AWS Organizations is enabled.
            return

        region = Stack.of(self).region

        name_with_region = f"{name}-{region}"
        if len(name_with_region) > 64:
            hex_digest = hashlib.sha256(name_with_region.encode("utf-8")).hexdigest()

            name_with_region = "".join(
                [
                    name_with_region[:50],
                    hex_digest[:4],
                ]
            )

        lambda_managed_policy = aws_iam.ManagedPolicy(
            self,
            "ram-accept-share-policy",
            managed_policy_name=name_with_region,
            description="Grants permission to read and accept RAM resource shares for a custom CF resource.",
            path="/VirtualWorkbench/",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "ram:AcceptResourceShareInvitation",
                        "ram:GetResourceShareInvitations",
                    ],
                    resources=["*"],
                )
            ],
        )

        func = backend_app_function.BackendAppFunction(
            self,
            "handler",
            app_root="infra",
            entry="infra/handler",
            lambda_root="infra/constructs/ssm/handler",
            layers=[],
            function_name=name_with_region,
            reserved_concurrency=1,
            provisioned_concurrency=None,
            timeout=Duration.seconds(15),
            memory_size=256,
            permissions=[
                lambda f: f.role.add_managed_policy(lambda_managed_policy),
                lambda f: f.role.add_managed_policy(
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ),
            ],
            local_bundling=True,
        )

        service_provider_role = aws_iam.Role(
            self,
            "service-provider-role",
            role_name=f"{name_with_region}-sp",
            path="/VirtualWorkbench/",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        ram_share_accept_provider = custom_resources.Provider(
            self,
            "ram-accept-provider",
            on_event_handler=func.function,
            role=service_provider_role,
        )

        CustomResource(
            self,
            "ram-accept",
            service_token=ram_share_accept_provider.service_token,
            properties={"Name": name},
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
            ram_share_accept_provider,
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

    def read_imported_ssm_parameter(
        self, account: str, parameter_name: str, region: str | None = None
    ) -> aws_ssm.IStringParameter:

        return aws_ssm.StringParameter.from_string_parameter_arn(
            self,
            f"SSMParameter-{account}-{parameter_name}",
            string_parameter_arn=Stack.of(self).format_arn(
                partition="aws",
                account=account,
                region=region,
                service="ssm",
                resource="parameter",
                resource_name=parameter_name.strip("/"),
                arn_format=ArnFormat.SLASH_RESOURCE_NAME,
            ),
        )
