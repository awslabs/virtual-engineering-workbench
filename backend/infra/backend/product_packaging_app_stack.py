import aws_cdk
import cdk_nag
import constructs
from aws_cdk import (
    ArnFormat,
    Duration,
    aws_ec2,
    aws_ecr,
    aws_iam,
    aws_s3,
)

from infra import config, constants
from infra.constructs.iam import role
from infra.constructs.s3 import bucket
from infra.constructs.sns import topic


class ProductPackagingAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        web_application_account: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Role assumed by the packaging bounded context to perform EC2 Image Builder actions
        self.__product_packaging_admin_role = role.Role(
            self,
            "ProductPackagingAdminRole",
            assumed_by=aws_iam.AccountPrincipal(account_id=web_application_account)
            .with_conditions(
                {
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": self.format_arn(
                            account=web_application_account,
                            partition=self.partition,
                            region="",
                            resource="role",
                            resource_name=app_config.format_resource_name_with_component("packaging", "*"),
                            service="iam",
                        ),
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
            description="Role used by packaging to interact with the EC2 Image Builder service.",
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSImageBuilderFullAccess")],
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:DescribeInstances",
                            "ssm:GetCommandInvocation",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            "*",
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:RunInstances",
                            "ec2:TerminateInstances",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account if resource != "image" else "",
                                partition=self.partition,
                                region=self.region,
                                resource=resource,
                                resource_name="*",
                                service="ec2",
                            )
                            for resource in [
                                "image",
                                "instance",
                                "network-interface",
                                "security-group",
                                "subnet",
                                "volume",
                            ]
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ssm:DescribeParameters",
                            "ssm:GetParameter",
                            "ssm:GetParameterHistory",
                            "ssm:GetParameters",
                            "ssm:GetParametersByPath",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account="",
                                partition=self.partition,
                                region=self.region,
                                resource="parameter",
                                resource_name="aws/service/*",
                                service="ssm",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ssm:GetConnectionStatus",
                            "ssm:SendCommand",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="instance",
                                resource_name="*",
                                service="ec2",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ssm:SendCommand",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account="",
                                partition=self.partition,
                                region=self.region,
                                resource="document",
                                resource_name="*",
                                service="ssm",
                            ),
                        ],
                    ),
                ),
            ],
            role_name=constants.PRODUCT_PACKAGING_ADMIN_ROLE,
        )

        # Buckets required by components and recipes
        self.__components_definitions_bucket = bucket.Bucket(
            self,
            "ComponentsDefinitionsBucket",
            bucket_name=app_config.format_base_resource_name(constants.COMPONENTS_DEFINITIONS_BUCKET),
            lifecycle_rules=[
                aws_s3.LifecycleRule(
                    expiration=Duration.days(1),
                    noncurrent_version_expiration=Duration.days(1),
                    prefix="validation",
                ),
                aws_s3.LifecycleRule(expired_object_delete_marker=True),
            ],
        )
        self.__components_versions_tests_bucket = bucket.Bucket(
            self,
            "ComponentsVersionsTestsBucket",
            bucket_name=app_config.format_base_resource_name(constants.COMPONENTS_VERSIONS_TESTS_BUCKET),
            cors=[
                aws_s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[aws_s3.HttpMethods.GET],
                    allowed_origins=["*"],
                ),
            ],
        )
        self.__recipes_definitions_bucket = bucket.Bucket(
            self,
            "RecipesDefinitionsBucket",
            bucket_name=app_config.format_base_resource_name(constants.RECIPES_DEFINITIONS_BUCKET),
        )
        self.__recipes_versions_tests_bucket = bucket.Bucket(
            self,
            "RecipesVersionsTestsBucket",
            bucket_name=app_config.format_base_resource_name(constants.RECIPES_VERSIONS_TESTS_BUCKET),
            cors=[
                aws_s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[aws_s3.HttpMethods.GET],
                    allowed_origins=["*"],
                ),
            ],
        )

        # Prerequisites resources for EC2 Image Builder pipelines
        self.__artifacts_storage_bucket = bucket.Bucket(
            self,
            "ArtifactsStorageBucket",
            bucket_name=app_config.format_base_resource_name(constants.ARTIFACTS_STORAGE_RESOURCE_NAME),
        )

        # ECR Repository for docker images do be built-in in the AMIs
        self.__artifacts_storage_ecr_repo = aws_ecr.Repository(
            self,
            "ArtifactsStorageECRRepository",
            repository_name=app_config.format_resource_name(constants.ARTIFACTS_STORAGE_RESOURCE_NAME),
            image_tag_mutability=aws_ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=True,
        )

        # Role and instance profile for build and test instances
        self.__product_packaging_instance_role = role.Role(
            self,
            "ProductPackagingInstanceRole",
            assumed_by=aws_iam.ServicePrincipal(f"ec2.{self.url_suffix}"),
            description="Role assigned to the EC2 instances managed by the EC2 Image Builder service.",
            instance_profile_name=constants.PRODUCT_PACKAGING_INSTANCE_PROFILE,
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonInspectorFullAccess"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilder"),
            ],
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:AuthorizeSecurityGroupIngress",
                            "ec2:CreateSecurityGroup",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource=resource,
                                resource_name="*",
                                service="ec2",
                            )
                            for resource in ["security-group", "vpc"]
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:CreateKeyPair",
                            "ec2:DeleteKeyPair",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="key-pair",
                                resource_name="*",
                                service="ec2",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:CreateTags",
                            "ec2:DescribeImages",
                            "ec2:DescribeInstanceStatus",
                            "ec2:DescribeInstances",
                            "kms:ListAliases",
                            "ssm:ListCommandInvocations",
                            "ssm:SendCommand",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            "*",
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:RunInstances",
                            "ec2:TerminateInstances",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=(self.account if resource not in ["image", "snapshot"] else ""),
                                partition=self.partition,
                                region=self.region,
                                resource=resource,
                                resource_name="*",
                                service="ec2",
                            )
                            for resource in [
                                "image",
                                "instance",
                                "key-pair",
                                "network-interface",
                                "security-group",
                                "snapshot",
                                "subnet",
                                "volume",
                            ]
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "imagebuilder:*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region="*",
                                resource=resource_details["resource"],
                                resource_name=resource_details["resource_name"],
                                service="imagebuilder",
                            )
                            for resource_details in [
                                {"resource": "component", "resource_name": "*/*"},
                                {"resource": "component", "resource_name": "*/*/*"},
                                {
                                    "resource": "container-recipe",
                                    "resource_name": "*/*",
                                },
                                {
                                    "resource": "distribution-configuration",
                                    "resource_name": "*",
                                },
                                {"resource": "image", "resource_name": "*/*"},
                                {"resource": "image", "resource_name": "*/*/*"},
                                {"resource": "image-pipeline", "resource_name": "*"},
                                {"resource": "image-recipe", "resource_name": "*/*"},
                                {
                                    "resource": "infrastructure-configuration",
                                    "resource_name": "*",
                                },
                            ]
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "imagebuilder:*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region="*",
                                resource="key",
                                resource_name="*",
                                service="kms",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                arn_format=ArnFormat.COLON_RESOURCE_NAME,
                                partition=self.partition,
                                region=self.region,
                                resource="log-group",
                                resource_name="*",
                                service="logs",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "s3:GetObject*",
                            "s3:ListBucket*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account="",
                                partition=self.partition,
                                region="",
                                resource=self.__artifacts_storage_bucket.bucket.bucket_name,
                                resource_name=resource_name,
                                service="s3",
                            )
                            for resource_name in [
                                None,
                                "*",
                            ]
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "sns:Publish",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region=self.region,
                                resource="*",
                                service="sns",
                            ),
                        ],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ecr:GetAuthorizationToken",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchCheckLayerAvailability",
                        ],
                        resources=[self.__artifacts_storage_ecr_repo.repository_arn],
                    ),
                ),
            ],
            role_name=constants.PRODUCT_PACKAGING_INSTANCE_ROLE,
        )

        # Security group for build and test instances
        self.__product_packaging_instance_security_group = aws_ec2.SecurityGroup(
            self,
            "ProductPackagingInstanceSecurityGroup",
            allow_all_outbound=True,
            description="Security group assigned to the EC2 instances managed by the EC2 Image Builder service.",
            disable_inline_rules=True,
            security_group_name=constants.PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP,
            vpc=aws_ec2.Vpc.from_lookup(
                self,
                "ProductPackagingVpc",
                vpc_name=app_config.component_specific.get("ami-factory-vpc-name"),
            ),
        )

        # Topic to receive images status notification
        self.__product_packaging_topic = topic.Topic(
            self,
            "ProductPackagingTopic",
            create_key=True,
            key_permissions=[
                lambda lambda_f: lambda_f.add_to_resource_policy(
                    aws_iam.PolicyStatement(
                        actions=[
                            "kms:Decrypt",
                            "kms:GenerateDataKey*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        principals=[
                            aws_iam.ArnPrincipal(
                                arn=self.format_arn(
                                    account=self.account,
                                    partition=self.partition,
                                    region="",
                                    resource="role",
                                    resource_name=f"aws-service-role/imagebuilder.{self.url_suffix}/AWSServiceRoleForImageBuilder",
                                    service="iam",
                                ),
                            ),
                        ],
                        resources=[
                            "*",
                        ],
                    ),
                ),
            ],
            topic_name=constants.PRODUCT_PACKAGING_TOPIC,
        )

        # Setup inter-resources permissions
        self.__setup_permissions(app_config=app_config, web_application_account=web_application_account)

        # Apply cdk-nag suppressions
        self.__apply_nag_suppressions()

    @property
    def components_definitions_bucket(self) -> bucket.Bucket:
        return self.__components_definitions_bucket

    @property
    def components_versions_tests_bucket(self) -> bucket.Bucket:
        return self.__components_versions_tests_bucket

    @property
    def artifact_storage_bucket(self) -> bucket.Bucket:
        return self.__artifacts_storage_bucket

    @property
    def product_packaging_admin_role(self) -> role.Role:
        return self.__product_packaging_admin_role

    @property
    def product_packaging_instance_role(self) -> role.Role:
        return self.__product_packaging_instance_role

    @property
    def product_packaging_instance_security_group(self) -> aws_ec2.ISecurityGroup:
        return self.__product_packaging_instance_security_group

    @property
    def product_packaging_topic(self) -> topic.Topic:
        return self.__product_packaging_topic

    @property
    def recipes_definitions_bucket(self) -> bucket.Bucket:
        return self.__recipes_definitions_bucket

    @property
    def recipes_versions_tests_bucket(self) -> bucket.Bucket:
        return self.__recipes_versions_tests_bucket

    def __setup_permissions(self, app_config: config.AppConfig, web_application_account: str):
        # Permissions for admin role to instance role
        self.product_packaging_admin_role.role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "iam:GetRole",
                    "iam:ListInstanceProfilesForRole",
                ],
                resources=[
                    self.product_packaging_instance_role.role.role_arn,
                ],
            ),
        )
        self.product_packaging_instance_role.role.grant_pass_role(self.product_packaging_admin_role.role)

        # Permissions for admin role to topic
        self.product_packaging_admin_role.role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "kms:GenerateDataKey*",
                ],
                effect=aws_iam.Effect.ALLOW,
                resources=[
                    self.product_packaging_topic.key.key.key_arn,
                ],
            ),
        )
        self.product_packaging_topic.key.key.grant_decrypt(self.product_packaging_admin_role.role)
        self.product_packaging_topic.topic.grant_publish(self.product_packaging_admin_role.role)

        # Permissions for admin and instance roles to components and recipes buckets
        for role_construct in [
            self.product_packaging_admin_role,
            self.product_packaging_instance_role,
        ]:
            self.components_definitions_bucket.bucket.grant_read_write(role_construct.role)
            self.components_versions_tests_bucket.bucket.grant_read_write(role_construct.role)
            self.recipes_definitions_bucket.bucket.grant_read_write(role_construct.role)
            self.recipes_versions_tests_bucket.bucket.grant_read_write(role_construct.role)

        # Permissions for web application account to topic
        self.__product_packaging_topic.topic.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "sns:Subscribe",
                ],
                effect=aws_iam.Effect.ALLOW,
                principals=[
                    aws_iam.AccountPrincipal(account_id=web_application_account),
                ],
                resources=[
                    self.__product_packaging_topic.topic.topic_arn,
                ],
            ),
        )

    def __apply_nag_suppressions(self):
        for role_construct in [
            self.product_packaging_admin_role,
            self.product_packaging_instance_role,
        ]:
            role_policy = [_ for _ in role_construct.role.node.children if isinstance(_, aws_iam.Policy)][0]

            cdk_nag.NagSuppressions.add_resource_suppressions(
                role_construct.role.node.children,
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
            if role_construct is self.product_packaging_instance_role:
                cdk_nag.NagSuppressions.add_resource_suppressions(
                    role_policy,
                    [
                        cdk_nag.NagPackSuppression(
                            id="NIST.800.53.R5-IAMPolicyNoStatementsWithFullAccess",
                            reason="Full access is allowed for this use case.",
                        ),
                        cdk_nag.NagPackSuppression(
                            id="PCI.DSS.321-IAMPolicyNoStatementsWithFullAccess",
                            reason="Full access is allowed for this use case.",
                        ),
                    ],
                )
