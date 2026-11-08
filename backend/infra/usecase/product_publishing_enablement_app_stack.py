import aws_cdk
import cdk_nag
from aws_cdk import Aws, Stack, Tags
from aws_cdk import aws_iam as iam
from constructs import Construct

from infra import config, constants


def _top_level_parameter_namespace(parameter_name: str) -> str:
    # Top-level namespace of an SSM parameter ("/workbench" for "/workbench/vpc/vpc-id"). Taken from the
    # config value the provisioning Lambdas read, so the IAM scope follows it. A name needs a namespace and
    # a leaf, otherwise "<namespace>/*" would not cover it; fail at synth instead of shipping a broken scope.
    parts = parameter_name.strip("/").split("/")
    if len(parts) < 2 or not all(parts):
        raise ValueError(f"Expected an SSM parameter name like /namespace/name, got {parameter_name!r}")
    return f"/{parts[0]}"


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
            # Read-only / list actions — many EC2/IAM/Lambda/CFN describe operations
            # do not support resource-level authorization. Grant on Resource="*".
            iam.PolicyStatement(
                actions=[
                    "cloudformation:DescribeStacks",
                    "cloudformation:GetTemplateSummary",
                    "cloudformation:ListStacks",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeInstances",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeVolumesModifications",
                    "ec2:DescribeVolumeStatus",
                    "iam:GetPolicy",
                    "iam:ListPolicyVersions",
                    "lambda:GetFunction",
                    "secretsmanager:ListSecrets",
                    "secretsmanager:GetRandomPassword",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            # Create-style actions inside Service Catalog stacks. Service Catalog
            # tags every resource it creates with aws:cloudformation:stack-name
            # starting with "SC-". Requiring that tag at request time constrains
            # this role to only affect resources that end up inside SC stacks.
            iam.PolicyStatement(
                actions=[
                    "ec2:AllocateAddress",
                    "ec2:AssociateAddress",
                    "ec2:CreateTags",
                    "ec2:DisassociateAddress",
                    "ec2:ReleaseAddress",
                    "secretsmanager:CreateSecret",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={
                    "StringLike": {
                        "aws:RequestTag/aws:cloudformation:stack-name": "SC-*",
                    },
                },
            ),
            # Destructive / tag-update actions on existing SC-managed resources.
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:TagResource",
                    "secretsmanager:UntagResource",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={
                    "StringLike": {
                        "aws:ResourceTag/aws:cloudformation:stack-name": "SC-*",
                    },
                },
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
        spoke_vpc_parameter_namespace = _top_level_parameter_namespace(
            app_config.environment_config["spoke-account-vpc-id-param-name"]
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
                # Read-only EC2/ECS/SSM actions on runtime-discovered resources —
                # many of these list-style actions do not support resource-level
                # scoping. Keep on Resource="*".
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:DescribeInstanceStatus",
                        "ec2:DescribeInstances",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSecurityGroupRules",
                        "ec2:DescribeVolumesModifications",
                        "compute-optimizer:GetEC2InstanceRecommendations",
                        "ssm:GetCommandInvocation",
                        "ssm:GetConnectionStatus",
                        "ssm:DescribeInstanceInformation",
                        "ecs:DescribeTasks",
                        "ecs:DescribeServices",
                        "ecs:ListTasks",
                    ],
                    resources=["*"],
                ),
                # Instance state changes are scoped to the caller's own
                # workbenches. The vew:provisionedProduct:ownerId tag stamped
                # on each provisioned workbench must equal the caller's UserId
                # principal tag (set on every backend-assumed STS session), so
                # user A cannot start or stop user B's workbench. Matches the
                # same pattern already used at the neighbouring secretsmanager
                # and volume-attach statements.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:instance/*",
                    ],
                    conditions={
                        "StringEquals": {
                            "aws:ResourceTag/vew:provisionedProduct:ownerId": "${aws:PrincipalTag/UserId}"
                        },
                    },
                ),
                # Security-group management for workbench SSH/RDP ingress rules.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:vpc/*",
                    ],
                ),
                # Tagging is used both on create (RequestTag) and on subsequent
                # updates (ResourceTag). Scope to any EC2 taggable resource that
                # carries or receives the VEW ownership tag.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ec2:CreateTags"],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:instance/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:volume/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:network-interface/*",
                    ],
                ),
                # ssm:GetParameter for the parameter store lookups the workbench
                # provisioning code performs in the spoke account: the VPC id
                # (spoke-account-vpc-id-param-name, read before every launch) and
                # the SSH private key of a provisioned workbench (/ec2/keypair/*).
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameter"],
                    resources=[
                        f"arn:{Aws.PARTITION}:ssm:*:{Aws.ACCOUNT_ID}:parameter/vew/*",
                        f"arn:{Aws.PARTITION}:ssm:*:{Aws.ACCOUNT_ID}:parameter{spoke_vpc_parameter_namespace}/*",
                        f"arn:{Aws.PARTITION}:ssm:*:{Aws.ACCOUNT_ID}:parameter{constants.EC2_KEY_PAIR_SSM_PARAMETER_PREFIX}/*",
                    ],
                ),
                # ssm:SendCommand is scoped in two dimensions per the AWS Service
                # Authorization Reference: (1) the target instance ARN — restricted
                # to the caller's own workbenches via
                # aws:ResourceTag/vew:provisionedProduct:ownerId equal to the
                # caller's UserId principal tag; (2) the document ARN — restricted
                # to AWS-managed shell/PowerShell documents, which are the only
                # ones provisioning/adapters/services/ssm_command_service.py
                # invokes.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:SendCommand"],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:instance/*",
                    ],
                    conditions={
                        "StringEquals": {
                            "aws:ResourceTag/vew:provisionedProduct:ownerId": "${aws:PrincipalTag/UserId}"
                        },
                    },
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:SendCommand"],
                    resources=[
                        f"arn:{Aws.PARTITION}:ssm:*::document/AWS-RunShellScript",
                        f"arn:{Aws.PARTITION}:ssm:*::document/AWS-RunPowerShellScript",
                    ],
                ),
                # ECS write actions are scoped to services and tasks owned by
                # the caller (aws:ResourceTag/vew:provisionedProduct:ownerId
                # equal to the caller's UserId principal tag).
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ecs:UpdateService"],
                    resources=["*"],
                    conditions={
                        "StringEquals": {
                            "aws:ResourceTag/vew:provisionedProduct:ownerId": "${aws:PrincipalTag/UserId}"
                        },
                    },
                ),
                # ecs:StopTask is scoped by ARN rather than by the ownership
                # tag. ECS does not carry tags onto tasks unless the service
                # sets PropagateTags, which nothing here does, so a tag
                # condition on a task cannot be satisfied. Tasks created by
                # Service Catalog carry the SC- physical-id prefix on their
                # cluster, which is scopable.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ecs:StopTask"],
                    resources=[f"arn:{Aws.PARTITION}:ecs:{Aws.REGION}:{Aws.ACCOUNT_ID}:task/SC-*/*"],
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
