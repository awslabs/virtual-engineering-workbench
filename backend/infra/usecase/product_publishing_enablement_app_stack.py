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
                    # Service Catalog reads these two after RunInstances
                    # succeeds, while reconciling the provisioned product's
                    # resource view. Neither supports resource-level
                    # authorization, so Resource="*".
                    "ec2:DescribeInstanceAttribute",
                    "ec2:DescribeInstanceCreditSpecifications",
                    "ec2:DescribeInstances",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    # Called by the Service Catalog / CloudFormation pre-flight
                    # immediately before CreateSecurityGroup, alongside the
                    # already-granted DescribeSubnets and
                    # DescribeSecurityGroups. EC2 Describe* actions do not
                    # support resource-level permissions, so Resource="*" is the
                    # only valid form and this is not a widening of the
                    # statement's existing scope.
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
                    # Both are CloudFormation IAM-provider pre-flight reads.
                    # Neither is retried, this repo has no call site for either,
                    # and iam:GetPolicy on the same policy ARN succeeds, so the
                    # provider obtains what it needs another way.
                    # iam:GetAccountSummary also only accepts Resource="*", so
                    # it cannot be scoped at all. The denials are log noise;
                    # listed here so they are not mistaken for an oversight.
                    #
                    # Granted below: also called post-RunInstances by Service Catalog.
                    # ssm:ListAssociations does not support resource-level
                    # authorization.
                    "ssm:ListAssociations",
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
            # ec2:CreateTags for the resources Service Catalog templates create.
            #
            # This statement exists because the preceding statement's condition
            # key, aws:RequestTag/aws:cloudformation:stack-name, can never be
            # satisfied for ec2:CreateTags. The "aws:" tag prefix is reserved by
            # AWS (see the CloudFormation resource-tagging reference), and EC2
            # does not surface reserved tag keys as aws:RequestTag/* condition
            # keys at authorization time. CloudFormation does send
            # aws:cloudformation:stack-name among the tags on the call, but AWS
            # supplies no aws:RequestTag/* keys in the authorization context, so
            # the StringLike condition cannot match and the call fails with
            # "no identity-based policy allows the ec2:CreateTags action".
            #
            # The fix keeps a tag condition rather than dropping it, but keys it
            # on a NON-reserved tag that VEW itself stamps on every provisioned
            # product and that Service Catalog propagates to every resource in
            # the stack: vew:provisionedProduct:id (see
            # product_provisioning_aggregate). Verified with the IAM policy
            # simulator against a full 20-tag request: allowed, while
            # a request without the tag, and a request whose value does not
            # match vew-pp-*, are both still denied.
            #
            # ec2:CreateTags is deliberately left in the statement above too:
            # removing it there would be an unrelated change, and it is inert
            # rather than harmful (its condition simply never matches).
            iam.PolicyStatement(
                actions=["ec2:CreateTags"],
                resources=[
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group/*",
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:instance/*",
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:volume/*",
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:network-interface/*",
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:key-pair/*",
                    f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:elastic-ip/*",
                ],
                effect=iam.Effect.ALLOW,
                conditions={
                    "StringLike": {
                        "aws:RequestTag/vew:provisionedProduct:id": "vew-pp-*",
                    },
                },
            ),
            # Same create-style actions, keyed on the VEW-owned tag instead of the
            # reserved aws:cloudformation:stack-name. Reserved aws: tags are not surfaced
            # as condition keys, so the statement above is not relied on; this one is.
            # vew:provisionedProduct:id (vew-pp-<uuid>) is set by the provisioning
            # aggregate and propagated by Service Catalog to every stack resource.
            # Additive: the statement above is left unchanged.
            iam.PolicyStatement(
                actions=["ec2:AllocateAddress", "secretsmanager:CreateSecret"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={"StringLike": {"aws:RequestTag/vew:provisionedProduct:id": "vew-pp-*"}},
            ),
            # Teardown / tag-update actions on existing resources of a VEW-provisioned
            # product, keyed on the VEW-owned tag. The aws:ResourceTag/aws:cloudformation:
            # stack-name statement below relies on a reserved key and is not relied on.
            # Additive: that statement is left unchanged.
            iam.PolicyStatement(
                actions=[
                    "ec2:AssociateAddress",
                    "ec2:DisassociateAddress",
                    "ec2:ReleaseAddress",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:TagResource",
                    "secretsmanager:UntagResource",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={"StringLike": {"aws:ResourceTag/vew:provisionedProduct:id": "vew-pp-*"}},
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
            # Service Catalog (userAgent/invokedBy: servicecatalog.amazonaws.com),
            # acting as the CloudFormation AWS::IAM::Role resource provider,
            # enumerates the inline and attached policies of the
            # provisioned-product instance role IT CREATED, as part of the
            # detach -> delete-policies -> DeleteRole teardown sequence and the
            # post-delete reconciliation read.
            #
            # List-only, and strictly narrower than the iam write statement
            # already granted on role/* in this same policy (which permits
            # CreateRole/DeleteRole/PutRolePolicy/GetRolePolicy on every role in
            # the account). Without these the provider cannot confirm via List*
            # that the role is empty, so it falls back to polling GetRole until
            # the role is gone, which is most of the time the delete takes.
            # Scoped to role/SC-* to match this file's existing policy/SC-*,
            # log-group:SC-* and function:SC-* conventions, and verified with
            # the IAM policy simulator: allowed on the SC-* instance role,
            # implicitDeny on role/Admin.
            iam.PolicyStatement(
                actions=["iam:ListRolePolicies", "iam:ListAttachedRolePolicies"],
                resources=[f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            # The CloudFormation SecretsManager resource provider reads the
            # secret's metadata back after CreateSecret and again during
            # DeleteSecret. The secret holds the DCV user credential for the
            # workbench session. Without this both reads retry with backoff,
            # continuing after the resource is already reported deleted.
            # DescribeSecret supports resource-level ARNs, so it is scoped to
            # secret:SC-* rather than added to the Resource="*" read statement.
            iam.PolicyStatement(
                actions=["secretsmanager:DescribeSecret"],
                resources=[f"arn:{Aws.PARTITION}:secretsmanager:{Aws.REGION}:{Aws.ACCOUNT_ID}:secret:SC-*"],
                effect=iam.Effect.ALLOW,
            ),
            # Service Catalog / CloudFormation pre-flight capacity check, run
            # immediately before CreateSecurityGroup, against the "VPC security
            # groups per Region" quota. The role has no servicequotas statement
            # otherwise — a missing service rather than a missing action. The
            # denial fails open: in an account near the quota the provider loses
            # the ability to fail fast with "quota exceeded" and instead fails
            # late inside CreateSecurityGroup with a less actionable error.
            #
            # Scoped to vpc/* only, the single quota namespace this path reads.
            # An ec2/* instance-quota check is plausible but has not been
            # observed, so it is deliberately not granted; add it only if a
            # denial actually appears.
            iam.PolicyStatement(
                actions=["servicequotas:GetServiceQuota"],
                resources=[f"arn:{Aws.PARTITION}:servicequotas:{Aws.REGION}:{Aws.ACCOUNT_ID}:vpc/*"],
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
                # cloudformation:ListStackResources is called through this role
                # by Service Catalog (userAgent servicecatalog.amazonaws.com)
                # while reconciling the provisioned product's resource view,
                # in the same 1-second burst as
                # servicecatalog:DescribeProvisionedProduct /
                # servicecatalog:DescribeRecord / cloudformation:DescribeStacks
                # that assembles the "your workbench is ready" view. The denial
                # is swallowed silently — no application-level error is raised —
                # so the UI keeps the stack-level facts (DescribeStacks) and the
                # instance (DescribeInstances) but loses the itemised resource
                # list.
                #
                # Kept as a separate statement rather than appended to the
                # Resource="*" statement above because ListStackResources does
                # support a stack ARN, so it can be scoped to SC-* stacks.
                # Narrowing the five actions above is deliberately not done
                # here: cloudformation:ListStacks requires Resource="*" and
                # scoping it would break them.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["cloudformation:ListStackResources"],
                    resources=[f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/SC-*/*"],
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
                        # ec2:DescribeImages is called by
                        # ec2_instance_management_service.get_instance_platform()
                        # (ec2_instance_management_service.create_user_security_group)
                        # to read PlatformDetails off the instance's AMI.
                        # ec2:DescribeNetworkInterfaces is called by
                        # describe_subnet_interfaces() (same file, :440).
                        # Both are non-test call sites and neither action was
                        # ever present in this policy, so both features failed.
                        # EC2 Describe* actions do not support resource-level
                        # permissions, so Resource="*" is correct.
                        "ec2:DescribeImages",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSubnets",
                        # ec2:DescribeVpcs is denied on both this role and the
                        # launch-constraint role, confirmed with the IAM policy
                        # simulator against a passing DescribeSubnets control.
                        # There is a real non-test call site:
                        # projects/adapters/services/ec2_network_service
                        # and :43, reached from the account-onboarding and
                        # dynamic-resource-setup path. EC2 Describe* does not
                        # support resource-level permissions, so Resource="*" is
                        # correct and is not a widening of this statement's
                        # existing scope.
                        "ec2:DescribeVpcs",
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
                # NOTE: AuthorizeSecurityGroupIngress / RevokeSecurityGroupIngress
                # authorize against TWO distinct resource types, because the call
                # creates (or deletes) security-group-RULE objects which AWS models
                # as their own resource type, separate from their parent group:
                #   security-group/*      - the group the rule is attached to
                #   security-group-rule/* - the rule object itself
                # Omitting security-group-rule/* makes every call fail with
                # UnauthorizedOperation naming
                # arn:aws:ec2:<region>:<account>:security-group-rule/* as the
                # denied resource, even though security-group/<id> is allowed.
                # Reached from
                # ec2_instance_management_service.authorize_user_ip_address.
                # CreateSecurityGroup needs security-group/* + vpc/*.
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group-rule/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:vpc/*",
                    ],
                ),
                # Tagging happens both on create and on subsequent updates.
                # Scoped by ARN to the EC2 resource types a workbench launch
                # tags; there is no tag condition here, because tag-on-create
                # cannot require a tag that the call is itself setting.
                # security-group-rule/* is required for tag-on-create: both
                # create_security_group and authorize_security_group_ingress pass
                # TagSpecifications (ResourceType "security-group" and
                # "security-group-rule" respectively), and tag-on-create requires
                # ec2:CreateTags on the resource type being tagged.
                # See ec2_instance_management_service.py create_user_security_group
                # (ResourceType "security-group") and authorize_user_ip_address
                # (ResourceType "security-group-rule").
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ec2:CreateTags"],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:instance/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group/*",
                        f"arn:{Aws.PARTITION}:ec2:*:{Aws.ACCOUNT_ID}:security-group-rule/*",
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
