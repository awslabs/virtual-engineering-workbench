import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam, aws_kms

from infra import config, constants
from infra.constructs.iam import role


class ImageSharingAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        keys: list[aws_kms.Key],
        regions: list[str],
        web_application_account: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Role assumed by the publishing bounded context to share images
        self.__product_publishing_image_service_role = role.Role(
            self,
            "ProductPublishingImageServiceRole",
            assumed_by=aws_iam.AccountPrincipal(account_id=web_application_account)
            .with_conditions(
                {
                    "ForAllValues:StringLike": {
                        "aws:PrincipalArn": self.format_arn(
                            account=web_application_account,
                            partition=self.partition,
                            region="",
                            resource="role",
                            resource_name=app_config.format_resource_name_with_component("publishing", "*"),
                            service="iam",
                        ),
                        "aws:RequestTag/UserId": "*",
                    }
                }
            )
            .with_session_tags(),
            description="Role used by publishing to distribute images across accounts and regions.",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("Ec2ImageBuilderCrossAccountDistributionAccess")
            ],
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "kms:CreateGrant",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                            "kms:ReEncrypt*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[key.key_arn for key in keys],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ecr:GetRepositoryPolicy",
                            "ecr:SetRepositoryPolicy",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            self.format_arn(
                                account=self.account,
                                partition=self.partition,
                                region="*",
                                resource="repository",
                                resource_name=app_config.format_base_resource_name("container-images-repo"),
                                service="ecr",
                            ),
                        ],
                    ),
                ),
            ],
            role_name=constants.PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE,
        )

        # Role assumed by the packaging bounded context to clean up unused images
        self.__packaging_image_service_role = role.Role(
            self,
            "PackagingImageServiceRole",
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
            description="Role used by packaging bounded context to clean up unused images",
            permissions=[
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "kms:CreateGrant",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                            "kms:ReEncrypt*",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[key.key_arn for key in keys],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=["ec2:DeregisterImage"],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=["ec2:DeleteSnapshot"],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ec2:DescribeImages",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ),
                lambda lambda_f: lambda_f.add_to_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "imagebuilder:DeleteImage",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                ),
            ],
            role_name=constants.PACKAGING_IMAGE_SERVICE_ROLE,
        )

        # Apply cdk-nag suppressions
        self.__apply_nag_suppressions()

    @property
    def product_publishing_image_service_role(self) -> role.Role:
        return self.__product_publishing_image_service_role

    @property
    def packaging_image_service_role(self) -> role.Role:
        return self.__packaging_image_service_role

    def __apply_nag_suppressions(self):
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.product_publishing_image_service_role.role.node.children,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Usage of managed policies is allowed for this use case.",
                ),
            ],
        )

        for role_construct in [
            self.product_publishing_image_service_role,
            self.packaging_image_service_role,
        ]:
            role_policy = [_ for _ in role_construct.role.node.children if isinstance(_, aws_iam.Policy)][0]

            cdk_nag.NagSuppressions.add_resource_suppressions(
                role_policy,
                [
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="Usage of wildcards is allowed for this use case.",
                    ),
                ],
            )
