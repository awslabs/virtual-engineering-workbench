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
                            "ec2:DescribeAddresses",
                            "ec2:DescribeAvailabilityZones",
                            # Service Catalog reads these two after RunInstances
                            # succeeds, while reconciling the provisioned
                            # product's resource view. Neither supports
                            # resource-level authorization, so Resource="*".
                            "ec2:DescribeInstanceAttribute",
                            "ec2:DescribeInstanceCreditSpecifications",
                            "ec2:DescribeInstances",
                            "ec2:DescribeKeyPairs",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            # Called by the Service Catalog / CloudFormation
                            # pre-flight immediately before
                            # CreateSecurityGroup, alongside the
                            # already-granted DescribeSubnets and
                            # DescribeSecurityGroups. EC2 Describe* actions do
                            # not support resource-level permissions, so
                            # Resource="*" is the only valid form.
                            "ec2:DescribeVpcs",
                            "ec2:DescribeVolumes",
                            "ec2:DescribeVolumesModifications",
                            "ec2:DescribeVolumeStatus",
                            "iam:GetPolicy",
                            "iam:ListPolicyVersions",
                            "lambda:GetFunction",
                            "secretsmanager:ListSecrets",
                            "secretsmanager:GetRandomPassword",
                            # Deliberately not granted:
                            #   iam:GetAccountSummary
                            #   iam:ListEntitiesForPolicy
                            # CloudFormation's IAM provider attempts both during
                            # pre-flight, but neither is retried, neither has a
                            # call site in this repo, and iam:GetPolicy on the
                            # same policy ARN succeeds regardless. The denials
                            # are log noise. iam:GetAccountSummary also only
                            # accepts Resource="*" and cannot be scoped at all.
                            # Listed here so they are not mistaken for an
                            # oversight.
                            #
                            # Granted below: also called post-RunInstances by Service Catalog.
                            # ssm:ListAssociations does not support
                            # resource-level authorization.
                            "ssm:ListAssociations",
                            "ecs:DescribeServices",
                        ],
                        resources=["*"],
                    )
                ),
                # Create-style actions inside Service Catalog stacks. Service
                # Catalog auto-tags every stack resource with
                # aws:cloudformation:stack-name starting with "SC-".
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ec2:AllocateAddress",
                            "ec2:AssociateAddress",
                            "ec2:CreateTags",
                            "ec2:DisassociateAddress",
                            "ec2:ReleaseAddress",
                            "secretsmanager:CreateSecret",
                            "ecs:RegisterTaskDefinition",
                            "ecs:DeregisterTaskDefinition",
                            "ecs:TagResource",
                            "ecs:CreateService",
                        ],
                        resources=["*"],
                        conditions={
                            "StringLike": {
                                "aws:RequestTag/aws:cloudformation:stack-name": "SC-*",
                            },
                        },
                    )
                ),
                # ec2:CreateTags for the resources Service Catalog templates
                # create.
                #
                # This statement exists because the preceding statement's
                # condition key, aws:RequestTag/aws:cloudformation:stack-name,
                # can never be satisfied for ec2:CreateTags. The "aws:" tag
                # prefix is reserved by AWS, and EC2 does not surface reserved
                # tag keys as aws:RequestTag/* condition keys at authorization
                # time. CloudFormation does stamp
                # aws:cloudformation:stack-name onto the resources it creates,
                # so the tag exists on the resource — but it never appears in
                # the authorization context, so a StringLike condition on it
                # cannot match and the call fails with "no identity-based
                # policy allows the ec2:CreateTags action".
                #
                # The fix keeps a tag condition rather than dropping it, but
                # keys it on a non-reserved tag that VEW itself stamps on every
                # provisioned product and that Service Catalog propagates to
                # every resource in the stack: vew:provisionedProduct:id.
                #
                # ec2:CreateTags is deliberately left in the statement above
                # too: removing it there would be an unrelated change, and it is
                # inert rather than harmful, since its condition simply never
                # matches. The spoke-side copy of this role in
                # infra/usecase/product_publishing_enablement_app_stack.py
                # carries the same fix.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["ec2:CreateTags"],
                        resources=[
                            f"arn:{self.partition}:ec2:*:{self.account}:security-group/*",
                            f"arn:{self.partition}:ec2:*:{self.account}:instance/*",
                            f"arn:{self.partition}:ec2:*:{self.account}:volume/*",
                            f"arn:{self.partition}:ec2:*:{self.account}:network-interface/*",
                            f"arn:{self.partition}:ec2:*:{self.account}:key-pair/*",
                            f"arn:{self.partition}:ec2:*:{self.account}:elastic-ip/*",
                        ],
                        conditions={
                            "StringLike": {
                                "aws:RequestTag/vew:provisionedProduct:id": "vew-pp-*",
                            },
                        },
                    )
                ),
                # Destructive / tag-update actions on existing SC-managed
                # resources.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "secretsmanager:DeleteSecret",
                            "secretsmanager:TagResource",
                            "secretsmanager:UntagResource",
                            "ecs:DeleteService",
                        ],
                        resources=["*"],
                        conditions={
                            "StringLike": {
                                "aws:ResourceTag/aws:cloudformation:stack-name": "SC-*",
                            },
                        },
                    )
                ),
                # ECS actions restored to a satisfiable form.
                #
                # The statement above grants ecs:RegisterTaskDefinition,
                # ecs:DeregisterTaskDefinition, ecs:TagResource and
                # ecs:CreateService, and the statement further down grants
                # ecs:DeleteService — but all five sit under conditions keyed on
                # aws:cloudformation:stack-name
                # (aws:RequestTag/... and aws:ResourceTag/... respectively).
                # "aws:" is an AWS-reserved tag prefix. CloudFormation really
                # does stamp aws:cloudformation:stack-name onto the resources it
                # creates, so the tag exists on the resource — but reserved keys
                # are never surfaced as aws:RequestTag/* or aws:ResourceTag/*
                # condition keys at authorization time. A caller cannot set them
                # (IAM rejects user-supplied "aws:"-prefixed tags) and the
                # service does not expose them. Those conditions therefore
                # cannot evaluate true for any principal, so the five grants are
                # permanently dead.
                #
                # ecs:DescribeServices is the one action left unconditioned, and
                # it is the one that still works. Confirmed in both directions
                # with the IAM policy simulator: the other five return
                # implicitDeny with no context, and allow once the reserved key
                # is injected manually.
                #
                # The spoke-side copy of this role grants all six ECS actions
                # unconditioned on Resource="*" and works, so the hub was both
                # more restrictive and broken.
                #
                # The fix does not restore Resource="*" wholesale. Scoping is
                # per-action, as tight as each action supports:
                #
                #  * ecs:RegisterTaskDefinition and ecs:DeregisterTaskDefinition
                #    do not support resource-level authorization, so "*" is the
                #    only form that can work. These are account-level actions;
                #    passing any task-definition ARN makes the simulator report
                #    implicitDeny even under a blanket ecs:* on "*", which is a
                #    simulator artefact rather than a policy defect.
                #  * ecs:CreateService, ecs:DeleteService and ecs:TagResource do
                #    support resource ARNs, so they are scoped to service/*/SC-*
                #    — Service Catalog names every stack resource with the SC-
                #    physical-id prefix. Verified against both a matching SC-*
                #    service name and a non-SC one, so the scope reaches what it
                #    must and nothing else.
                #  * ecs:TagResource additionally needs the task-definition
                #    resource type for tag-on-create of an
                #    AWS::ECS::TaskDefinition, whose family name is chosen by
                #    the product template author and is therefore not SC-*
                #    prefixed and cannot be scoped further than
                #    task-definition/*. Still strictly narrower than
                #    Resource="*".
                #
                # No tag condition is used. Keying on a non-reserved tag such as
                # aws:RequestTag/vew:provisionedProduct:id, the approach used
                # for ec2:CreateTags above, is verified for EC2 resources but
                # only inferred for ECS: no ECS product template exists in this
                # repo, so propagation to ECS resources cannot be observed.
                # Shipping a condition that cannot be verified is what made the
                # grants above dead, so this uses ARN scoping, which is
                # verifiable, instead.
                #
                # The dead statements above and below are deliberately left in
                # place. They are inert rather than harmful, and removing the
                # ECS actions from them would be an unrelated deletion.
                #
                # Scope note: the grant is verified by simulator readback with
                # positive and negative controls. No product template in this
                # repo creates an ECS service, so the end-to-end path cannot be
                # exercised until one exists.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ecs:RegisterTaskDefinition",
                            "ecs:DeregisterTaskDefinition",
                        ],
                        resources=["*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "ecs:CreateService",
                            "ecs:DeleteService",
                            "ecs:TagResource",
                        ],
                        resources=[f"arn:{self.partition}:ecs:{self.region}:{self.account}:service/*/SC-*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["ecs:TagResource"],
                        resources=[f"arn:{self.partition}:ecs:{self.region}:{self.account}:task-definition/*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=[
                            "cloudformation:CreateStack",
                            # cloudformation:UpdateStack is required because
                            # sc_products_service.update_provisioned_product()
                            # drives Service Catalog UpdateProvisionedProduct,
                            # which performs a CloudFormation stack UPDATE on
                            # the SC-* stack using this launch-constraint role.
                            # Needed here as well as on the spoke side.
                            "cloudformation:UpdateStack",
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
                            # Both shipped example products
                            # (examples/freertos/product.yaml and
                            # examples/android-cuttlefish/product.yaml)
                            # declare an AWS::EC2::KeyPair, so the launch
                            # constraint role must be able to create and delete
                            # key pairs. EC2 authorizes CreateKeyPair/
                            # DeleteKeyPair against the instance resource as
                            # well as the key-pair resource when the key pair is
                            # created as part of a RunInstances-bearing stack.
                            # Needed here as well as on the spoke side.
                            "ec2:CreateKeyPair",
                            "ec2:DeleteKeyPair",
                            "ec2:AttachVolume",
                            "ec2:DetachVolume",
                            "ec2:ModifyInstanceAttribute",
                            "ec2:StartInstances",
                        ],
                        resources=[f"arn:{self.partition}:ec2:{self.region}:{self.account}:instance/*"],
                    )
                ),
                # Key-pair actions. Required by both shipped example products,
                # which each declare an AWS::EC2::KeyPair.
                #
                # Note for future maintainers: most EC2 Describe*/Get*/List*
                # actions do not support resource-level permissions, so scoping
                # them to key-pair/* makes them effectively inert rather than
                # restrictive — the operative grant for describes is the
                # unconditioned Resource="*" statement at the top of this role.
                # The statement is kept in the same shape as the spoke-side copy
                # rather than tightened, so the two remain easy to diff.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
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
                        resources=[f"arn:{self.partition}:ec2:{self.region}:{self.account}:key-pair/*"],
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
                # Service Catalog, acting as the CloudFormation AWS::IAM::Role
                # resource provider, enumerates the inline and attached policies
                # of the provisioned-product instance role it created, as part
                # of the detach -> delete-policies -> DeleteRole teardown
                # sequence and the post-delete reconciliation read. Without
                # these the role delete retries until it eventually succeeds,
                # adding most of the time that step takes.
                #
                # List-only, and strictly narrower than the iam write statement
                # directly above, which already permits CreateRole / DeleteRole
                # / PutRolePolicy / GetRolePolicy on role/* in this account.
                # Scoped to role/SC-* to match this role's existing SC-*
                # conventions (stack/SC-*, log-group:SC-*, function:SC-*).
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["iam:ListRolePolicies", "iam:ListAttachedRolePolicies"],
                        resources=[f"arn:{self.partition}:iam::{self.account}:role/SC-*"],
                    )
                ),
                # The CloudFormation SecretsManager resource provider reads the
                # secret's metadata back after CreateSecret and again during
                # DeleteSecret, for the workbench's DCV user credential secret.
                # Without it both calls retry with backoff, continuing past the
                # point the stack reports complete. DescribeSecret supports
                # resource-level ARNs, so it is scoped to secret:SC-* rather
                # than added to the Resource="*" read statement.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["secretsmanager:DescribeSecret"],
                        resources=[f"arn:{self.partition}:secretsmanager:{self.region}:{self.account}:secret:SC-*"],
                    )
                ),
                # Service Catalog / CloudFormation pre-flight capacity check run
                # immediately before CreateSecurityGroup, against the "VPC
                # security groups per Region" quota. This role has no
                # servicequotas statement otherwise — a missing service rather
                # than a missing action. The denial fails open: in an account
                # near the quota the provider loses the ability to fail fast
                # with "quota exceeded" and fails late inside
                # CreateSecurityGroup instead.
                #
                # Scoped to vpc/* only, the one quota namespace this path uses.
                # An ec2/* instance-quota check is plausible but has not been
                # observed, so it is deliberately not granted.
                lambda lambda_f: lambda_f.add_to_policy(
                    PolicyStatement(
                        actions=["servicequotas:GetServiceQuota"],
                        resources=[f"arn:{self.partition}:servicequotas:{self.region}:{self.account}:vpc/*"],
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
                            # RunInstances is authorized against every resource
                            # it touches, including the key pair, when a
                            # template launches an instance with a KeyName.
                            # Both shipped example products do. Needed here as
                            # well as on the spoke side.
                            f"arn:{self.partition}:ec2:{self.region}:{self.account}:key-pair/*",
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
                        # ssm:GetParameters is used by CloudFormation to resolve
                        # AWS::SSM::Parameter::Value<String> template parameters
                        # (both shipped example products and the workbench
                        # template read /workbench/vpc/* this way).
                        #
                        # Reads only. No shipped product template declares an
                        # AWS::SSM::Parameter, and this role runs
                        # publisher-authored templates in the account that holds
                        # the workbench key-pair parameters, so write and delete
                        # are deliberately not granted here.
                        actions=[
                            "ssm:GetParameters",
                            "ssm:GetParameter",
                        ],
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
                            # CloudFormation stamps its stack tags onto log
                            # groups it creates, which requires logs:TagResource
                            # on the SC-* log groups.
                            "logs:TagResource",
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
                            # examples/android-cuttlefish/product.yaml
                            # declares an AWS::Lambda::Function, and
                            # CloudFormation stamps its stack tags onto it,
                            # which requires lambda:TagResource.
                            "lambda:TagResource",
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
        # Create-style and teardown actions on Service Catalog stack resources,
        # keyed on the VEW-owned tag vew:provisionedProduct:id (vew-pp-<uuid>)
        # instead of the reserved aws:cloudformation:stack-name. Reserved aws:
        # tags are not surfaced as condition keys, so the reserved-key statements
        # above are not relied on; these are. Additive: those statements are left
        # unchanged. A separate named policy keeps the role's default policy below
        # the size at which CDK splits it into an unsuppressed overflow policy.
        self.launch_constraint_vew_tag_policy = Policy(
            self,
            "LaunchConstraintVewTagPolicy",
            roles=[self.product_publishing_launch_constraint_role.role],
            statements=[
                PolicyStatement(
                    actions=["ec2:AllocateAddress", "secretsmanager:CreateSecret"],
                    resources=["*"],
                    conditions={"StringLike": {"aws:RequestTag/vew:provisionedProduct:id": "vew-pp-*"}},
                ),
                PolicyStatement(
                    actions=[
                        "ec2:AssociateAddress",
                        "ec2:DisassociateAddress",
                        "ec2:ReleaseAddress",
                        "secretsmanager:DeleteSecret",
                        "secretsmanager:TagResource",
                        "secretsmanager:UntagResource",
                    ],
                    resources=["*"],
                    conditions={"StringLike": {"aws:ResourceTag/vew:provisionedProduct:id": "vew-pp-*"}},
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.launch_constraint_vew_tag_policy,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=(
                        "Resource '*' is constrained by the vew:provisionedProduct:id tag condition: "
                        "these actions only apply to resources of a VEW-provisioned product."
                    ),
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
