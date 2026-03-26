import aws_cdk
import cdk_nag
from aws_cdk import Aws, Stack, Tags
from aws_cdk import aws_iam as iam
from constructs import Construct

from infra import config, constants


class ProductPublishingEnablementAppStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        app_config: config.AppConfig,
        image_service_account_id: str,
        catalog_service_account_id: str,
        web_application_account: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        role = iam.Role(
            self,
            "Role",
            role_name=constants.PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
            assumed_by=iam.ServicePrincipal(f"servicecatalog.{self.url_suffix}"),
        )

        # TODO: Remove V1 role later
        role_v1 = iam.Role(
            self,
            "RoleV1",
            role_name=constants.PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE.replace("V2", ""),
            assumed_by=iam.ServicePrincipal(f"servicecatalog.{self.url_suffix}"),
        )
        role_v1.apply_removal_policy(aws_cdk.RemovalPolicy.RETAIN)

        Tags.of(role).add("roletype", "launchconstraintrole")
        Tags.of(role_v1).add("roletype", "launchconstraintrole")

        policy_statements = [
            iam.PolicyStatement(
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
                    "iam:GetPolicy",
                    "iam:ListPolicyVersions",
                    "lambda:GetFunction",
                    "ec2:DescribeKeyPairs",
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
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "cloudformation:CreateStack",
                    "cloudformation:UpdateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:DescribeStackEvents",
                ],
                resources=[f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
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
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:*:security-group/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup"],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:*:vpc/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:AttachNetworkInterface",
                    "ec2:DetachNetworkInterface",
                    "ec2:ModifyNetworkInterfaceAttribute",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                    "ec2:StopInstances",
                    "ec2:CreateKeyPair",
                    "ec2:DeleteKeyPair",
                    "ec2:AttachVolume",
                    "ec2:DetachVolume",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:StartInstances",
                ],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:instance/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:Get*",
                    "ec2:List*",
                    "ec2:Describe*",
                    "ec2:DeleteTags",
                    "ec2:RunInstances",
                    "ec2:CreateKeyPair",
                    "ec2:DeleteKeyPair",
                    "ec2:DescribeKeyPairs",
                ],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:key-pair/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:CreateVolume",
                    "ec2:DeleteVolume",
                    "ec2:ModifyVolume",
                    "ec2:AttachVolume",
                    "ec2:DetachVolume",
                ],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:volume/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:DescribeKey", "kms:Encrypt", "kms:GenerateDataKey*", "kms:ReEncrypt*"],
                resources=[f"arn:{Aws.PARTITION}:kms:{Aws.REGION}:{image_service_account_id}:key/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:AddRoleToInstanceProfile",
                    "iam:CreateInstanceProfile",
                    "iam:DeleteInstanceProfile",
                    "iam:GetInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile",
                ],
                resources=[f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:instance-profile/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
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
                resources=[f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["kms:CreateGrant", "kms:GenerateDataKeyWithoutPlaintext"],
                resources=[f"arn:{Aws.PARTITION}:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:key/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:AttachNetworkInterface",
                    "ec2:DetachNetworkInterface",
                    "ec2:ModifyNetworkInterfaceAttribute",
                    "ec2:RunInstances",
                ],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:*:network-interface/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ec2:RunInstances"],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:*:subnet/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ec2:RunInstances"],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:volume/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ec2:RunInstances"],
                resources=[f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}::image/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={"StringEquals": {"s3:ExistingObjectTag/servicecatalog:provisioning": "true"}},
            ),
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[f"arn:{Aws.PARTITION}:sns:{Aws.REGION}:*:*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ssm:GetParameters", "ssm:PutParameter", "ssm:GetParameter", "ssm:DeleteParameter"],
                resources=[f"arn:{Aws.PARTITION}:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["iam:CreatePolicy", "iam:DeletePolicy"],
                resources=[f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:policy/SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:CreateLogGroup", "logs:TagResource"],
                resources=[f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "ecs:DeregisterTaskDefinition",
                    "ecs:RegisterTaskDefinition",
                    "ecs:TagResource",
                    "ecs:CreateService",
                    "ecs:DescribeServices",
                    "ecs:DeleteService",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "lambda:CreateFunction",
                    "lambda:DeleteFunction",
                    "lambda:InvokeFunction",
                    "lambda:TagResource",
                ],
                resources=[f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:function:SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                resources=[f"arn:{Aws.PARTITION}:kms:{Aws.REGION}:{catalog_service_account_id}:key/*"],
                effect=iam.Effect.ALLOW,
            ),
        ]

        iam.Policy(
            self,
            "Policy",
            policy_name="ProductPublishingLaunchConstraintRolePolicy",
            statements=policy_statements,
            roles=[role, role_v1],
        )

        # Product Publishing Use Case Role
        publishing_role_principal_regex = app_config.format_resource_name_with_component("publishing", "*")
        product_publishing_use_case_role = iam.Role(
            self,
            "ProductPublishingUseCaseRole",
            role_name=constants.PRODUCT_PUBLISHING_USE_CASE_ROLE,
            description="Role used by web app Publishing BC to do CRUD operations on Service Catalog portfolios, products and versions",
            assumed_by=iam.AccountPrincipal(account_id=web_application_account)
            .with_conditions(
                conditions={
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": f"arn:{Aws.PARTITION}:iam::{web_application_account}:role/{publishing_role_principal_regex}",
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
        )

        iam.Policy(
            self,
            "ProductPublishingUseCaseRolePolicy",
            policy_name="ProductPublishingUseCaseRolePolicy",
            roles=[product_publishing_use_case_role],
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW, actions=["iam:GetRole", "servicecatalog:*"], resources=["*"]
                )
            ],
        )

        # Workbench Web App Provisioning Role
        products_role_principal_regex = app_config.format_resource_name_with_component("products", "*")
        provisioning_role_principal_regex = app_config.format_resource_name_with_component("provisioning", "*")
        directory_services_role_principal_regex = app_config.format_resource_name_with_component(
            "directory-services", "*"
        )
        workbench_web_app_provisioning_role = iam.Role(
            self,
            "WorkbenchWebAppProvisioningRole",
            role_name=constants.PRODUCT_PROVISIONING_ROLE,
            description="Role used by web app Products BC to provision and terminate Service Catalog products on behalf of the user. VEW uses this role to provision workbenches published by Publishing BC.",
            assumed_by=iam.AccountPrincipal(account_id=web_application_account)
            .with_conditions(
                conditions={
                    "Null": {"aws:RequestTag/UserId": "false"},
                    "ForAnyValue:StringLike": {
                        "aws:PrincipalArn": [
                            f"arn:{Aws.PARTITION}:iam::{web_application_account}:role/{products_role_principal_regex}",
                            f"arn:{Aws.PARTITION}:iam::{web_application_account}:role/{provisioning_role_principal_regex}",
                            f"arn:{Aws.PARTITION}:iam::{web_application_account}:role/{directory_services_role_principal_regex}",
                        ],
                        "aws:RequestTag/UserId": "*",
                    },
                }
            )
            .with_session_tags(),
        )

        iam.Policy(
            self,
            "WorkbenchWebAppProvisioningRolePolicy",
            policy_name="WorkbenchWebAppProvisioningRolePolicy",
            roles=[workbench_web_app_provisioning_role],
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProvisioningArtifact",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:DescribeProvisionedProduct",
                        "servicecatalog:DescribeRecord",
                        "servicecatalog:GetProvisionedProductOutputs",
                        "servicecatalog:ListLaunchPaths",
                        "servicecatalog:ListProvisioningArtifacts",
                        "servicecatalog:ProvisionProduct",
                        "servicecatalog:SearchProducts",
                        "servicecatalog:SearchProvisionedProducts",
                        "servicecatalog:TerminateProvisionedProduct",
                        "servicecatalog:UpdateProvisionedProduct",
                    ],
                    resources=["*"],
                    conditions={"StringEquals": {"servicecatalog:accountLevel": "self"}},
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:GetTemplateSummary",
                        "cloudformation:ListStacks",
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:GetTemplate",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:GetObject"],
                    resources=["*"],
                    conditions={"StringEquals": {"s3:ExistingObjectTag/servicecatalog:provisioning": "true"}},
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:DescribeInstanceStatus",
                        "ec2:DescribeInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DescribeSecurityGroups",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:DescribeSecurityGroupRules",
                        "ec2:RevokeSecurityGroupIngress",
                        "ssm:GetParameter",
                        "compute-optimizer:GetEC2InstanceRecommendations",
                        "ssm:SendCommand",
                        "ssm:GetCommandInvocation",
                        "ssm:GetConnectionStatus",
                        "ssm:DescribeInstanceInformation",
                        "ecs:DescribeTasks",
                        "ecs:DescribeServices",
                        "ecs:ListTasks",
                        "ecs:UpdateService",
                        "ecs:StopTask",
                        "ec2:DescribeVolumesModifications",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=["*"],
                    conditions={
                        "StringEquals": {"aws:ResourceTag/vew:provisionedProduct:ownerId": "${aws:PrincipalTag/UserId}"}
                    },
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ec2:AttachVolume", "ec2:DetachVolume"],
                    resources=["*"],
                    conditions={
                        "StringEquals": {"aws:ResourceTag/vew:provisionedProduct:ownerId": "${aws:PrincipalTag/UserId}"}
                    },
                ),
            ],
        )

        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=Stack.of(self),
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMPolicyNoStatementsWithFullAccess",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMPolicyNoStatementsWithFullAccess",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )
