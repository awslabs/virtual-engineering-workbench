import aws_cdk.aws_s3_deployment as s3deploy
import cdk_nag
from aws_cdk import Stack
from aws_cdk.aws_iam import AccountPrincipal, ManagedPolicy, Policy, PolicyStatement, ServicePrincipal
from constructs import Construct

from infra import config
from infra.constants import (
    PRODUCT_PUBLISHING_ADMIN_ROLE,
    PRODUCT_PUBLISHING_CONFIGURATION_ROLE,
    PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
)
from infra.constructs.iam import role
from infra.constructs.s3 import bucket


class ProductPublishingAppStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        app_config: config.AppConfig,
        image_service_account_id: str,
        web_app_account_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Products Templates bucket
        products_templates_bucket = bucket.Bucket(
            self,
            "ProductsTemplatesBucket",
            bucket_name=app_config.component_specific["templates-s3-bucket-name"].format(
                environment=app_config.environment,
                tools_account_id=app_config.account,
                region=app_config.region,
            ),
            force_bucket_name_uniqueness=False,
        )

        self.products_templates_bucket_deployment = s3deploy.BucketDeployment(
            self,
            "ProductsTemplatesBucketDeployment",
            destination_bucket=products_templates_bucket.bucket,
            destination_key_prefix="templates",
            sources=[s3deploy.Source.asset("infra/backend/resources/product_publishing_app_stack/templates")],
        )

        # Role assumed by the configuration bounded context to configure the catalog service account
        self.product_publishing_configuration_role = role.Role(
            self,
            "ProductPublishingConfigurationRole",
            assumed_by=AccountPrincipal(web_app_account_id)
            .with_conditions(
                {
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": [
                            self.format_arn(
                                account=web_app_account_id,
                                resource="role",
                                resource_name=app_config.format_resource_name_with_component("configuration", "*"),
                                service="iam",
                                region="",
                            )
                        ],
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
            description="Role used by configuration to manage log groups.",
            role_name=PRODUCT_PUBLISHING_CONFIGURATION_ROLE,
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=PolicyStatement(
                        actions=[
                            "logs:DescribeLogGroups",
                            "logs:PutRetentionPolicy",
                        ],
                        resources=["*"],
                    )
                ),
            ],
        )

        # Product Publishing Admin Role
        self.product_publishing_admin_role = role.Role(
            self,
            "ProductPublishingAdminRole",
            assumed_by=AccountPrincipal(web_app_account_id)
            .with_conditions(
                {
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": [
                            self.format_arn(
                                account=web_app_account_id,
                                resource="role",
                                resource_name=app_config.format_resource_name_with_component("publishing", "*"),
                                service="iam",
                                region="",
                            )
                        ],
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitFullAccess"),
                ManagedPolicy.from_aws_managed_policy_name("AWSServiceCatalogAdminFullAccess"),
            ],
            role_name=PRODUCT_PUBLISHING_ADMIN_ROLE,
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=PolicyStatement(actions=["cloudformation:ValidateTemplate"], resources=["*"])
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=PolicyStatement(
                        actions=[
                            "kms:Decrypt",
                            "kms:DescribeKey",
                            "kms:Encrypt",
                            "kms:GenerateDataKey*",
                            "kms:ReEncrypt*",
                        ],
                        resources=[f"arn:{self.partition}:kms:*:{image_service_account_id}:key/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["s3:GetObject"],
                        conditions={"StringEquals": {"s3:ExistingObjectTag/servicecatalog:provisioning": True}},
                        resources=["*"],
                    )
                ),
            ],
        )

        products_templates_bucket.bucket.grant_read_write(self.product_publishing_admin_role.role)

        # Product Publishing Launch Constraint Role
        self.product_publishing_launch_constraint_role = role.Role(
            self,
            PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
            assumed_by=ServicePrincipal(f"servicecatalog.{self.url_suffix}"),
            role_name=PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "cloudformation:DescribeStacks",
                            "cloudformation:GetTemplateSummary",
                            "cloudformation:ListStacks",
                            "ec2:AllocateAddress",
                            "ec2:AssociateAddress",
                            "ec2:CreateTags",
                            "ec2:DescribeAddresses",
                            "ec2:DescribeAvailabilityZones",
                            "ec2:DescribeKeyPairs",
                            "ec2:DescribeInstances",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            "lambda:GetFunction",
                            "iam:GetPolicy",
                            "iam:ListPolicyVersions",
                            "ec2:DescribeVolumes",
                            "ec2:DescribeVolumeStatus",
                            "ec2:DescribeVolumesModifications",
                            "ec2:DisassociateAddress",
                            "ec2:ReleaseAddress",
                            "secretsmanager:CreateSecret",
                            "secretsmanager:DeleteSecret",
                            "secretsmanager:ListSecrets",
                            "secretsmanager:TagResource",
                            "secretsmanager:UntagResource",
                            "secretsmanager:GetRandomPassword",
                            "ecs:RegisterTaskDefinition",
                            "ecs:DeregisterTaskDefinition",
                            "ecs:TagResource",
                            "ecs:CreateService",
                            "ecs:DescribeServices",
                            "ecs:DeleteService",
                        ],
                        resources=["*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "cloudformation:CreateStack",
                            "cloudformation:DeleteStack",
                            "cloudformation:DescribeStackEvents",
                        ],
                        resources=[f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/SC-*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ec2:AuthorizeSecurityGroupEgress",
                            "ec2:AuthorizeSecurityGroupIngress",
                            "ec2:CreateSecurityGroup",
                            "ec2:DeleteSecurityGroup",
                            "ec2:ModifyNetworkInterfaceAttribute",
                            "ec2:RevokeSecurityGroupEgress",
                            "ec2:RevokeSecurityGroupIngress",
                            "ec2:RunInstances",
                        ],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:*:security-group/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup"],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:*:vpc/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ec2:AttachNetworkInterface",
                            "ec2:DetachNetworkInterface",
                            "ec2:ModifyNetworkInterfaceAttribute",
                            "ec2:RunInstances",
                            "ec2:TerminateInstances",
                            "ec2:StopInstances",
                            "ec2:AttachVolume",
                            "ec2:DetachVolume",
                            "ec2:ModifyInstanceAttribute",
                            "ec2:StartInstances",
                        ],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:{self.account}:instance/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "iam:AddRoleToInstanceProfile",
                            "iam:CreateInstanceProfile",
                            "iam:DeleteInstanceProfile",
                            "iam:GetInstanceProfile",
                            "iam:RemoveRoleFromInstanceProfile",
                        ],
                        resources=[f"arn:{self.partition}:iam::{self.account}:instance-profile/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "iam:AttachRolePolicy",
                            "iam:CreateRole",
                            "iam:DeleteRole",
                            "iam:DeleteRolePolicy",
                            "iam:DetachRolePolicy",
                            "iam:GetRole",
                            "iam:GetRolePolicy",
                            "iam:PassRole",
                            "iam:PutRolePolicy",
                            "iam:TagRole",
                            "iam:UntagRole",
                        ],
                        resources=[f"arn:{self.partition}:iam::{self.account}:role/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ec2:CreateVolume",
                            "ec2:DeleteVolume",
                            "ec2:ModifyVolume",
                            "ec2:AttachVolume",
                            "ec2:DetachVolume",
                        ],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:{self.account}:volume/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "kms:CreateGrant",
                            "kms:GenerateDataKeyWithoutPlaintext",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                            "kms:Encrypt",
                            "kms:GenerateDataKey*",
                            "kms:ReEncrypt*",
                        ],
                        resources=[f"arn:{self.partition}:kms:{self.region}:{image_service_account_id}:key/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["kms:CreateGrant", "kms:GenerateDataKeyWithoutPlaintext"],
                        resources=[f"arn:{self.partition}:kms:{self.region}:{self.account}:key/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ec2:AttachNetworkInterface",
                            "ec2:DetachNetworkInterface",
                            "ec2:ModifyNetworkInterfaceAttribute",
                            "ec2:RunInstances",
                        ],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:*:network-interface/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["ec2:RunInstances"],
                        resources=[
                            f"arn:{self.partition}:ec2:{self.region}:*:subnet/*",
                            f"arn:{self.partition}:ec2:{self.region}:{self.account}:volume/*",
                            f"arn:{self.partition}:ec2:{self.region}::image/*",
                        ],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["s3:GetObject"],
                        conditions={"StringEquals": {"s3:ExistingObjectTag/servicecatalog:provisioning": True}},
                        resources=["*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["sns:Publish"],
                        resources=[f"arn:{self.partition}:sns:{self.region}:*:*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["ssm:GetParameters"],
                        resources=[f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["iam:CreatePolicy", "iam:DeletePolicy"],
                        resources=[f"arn:{self.partition}:iam::{self.account}:policy/SC-*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "logs:DeleteLogGroup",
                            "logs:CreateLogGroup",
                            "logs:PutRetentionPolicy",
                        ],
                        resources=[f"arn:{self.partition}:logs:{self.region}:{self.account}:log-group:SC-*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "lambda:CreateFunction",
                            "lambda:DeleteFunction",
                            "lambda:InvokeFunction",
                        ],
                        resources=[f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:SC-*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["kms:Decrypt", "kms:GenerateDataKey"],
                        resources=[f"arn:{self.partition}:kms:*:{self.account}:key/*"],
                    )
                ),
            ],
        )
        self.__apply_nag_suppressions()

    def __apply_nag_suppressions(self):
        for role_construct in [
            self.product_publishing_admin_role.role,
            self.product_publishing_configuration_role.role,
            self.product_publishing_launch_constraint_role.role,
            self.products_templates_bucket_deployment.handler_role,
        ]:
            role_policy = [_ for _ in role_construct.node.children if isinstance(_, Policy)][0]

            cdk_nag.NagSuppressions.add_resource_suppressions(
                role_construct.node.children,
                [
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM4",
                        reason="Usage of managed policies is allowed for this use case.",
                    ),
                ],
            )
            cdk_nag.NagSuppressions.add_resource_suppressions(
                role_policy,
                [
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="Usage of wildcards is allowed for this use case.",
                    ),
                ],
            )

        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=self,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-LambdaInsideVPC",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaConcurrency",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaDLQ",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaInsideVPC",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-LambdaInsideVPC",
                    reason="Autogenerated by CDK.",
                ),
                cdk_nag.NagPackSuppression(id="NIST.800.53.R4-IAMNoInlinePolicy", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(id="NIST.800.53.R5-IAMNoInlinePolicy", reason="Autogenerated by CDK."),
                cdk_nag.NagPackSuppression(id="PCI.DSS.321-IAMNoInlinePolicy", reason="Autogenerated by CDK."),
            ],
        )
