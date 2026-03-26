import aws_cdk
import constructs
from aws_cdk import aws_iam

from infra import config
from infra.constructs.kms import key


class ImageKeyAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        id_suffix: str,
        organization_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Key used to encrypt/decrypt the images created by the packaging bounded context
        self.__key = key.Key(
            self,
            "Key",
            alias=app_config.format_resource_name_with_component_without_environment("key", "image"),
            description="Key used to encrypt/decrypt images.",
            permissions=[
                lambda lambda_f: lambda_f.add_to_resource_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "kms:CreateGrant",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                            "kms:Encrypt",
                            "kms:GenerateDataKey*",
                            "kms:ListGrants",
                            "kms:ReEncrypt*",
                            "kms:RevokeGrant",
                        ],
                        conditions={"StringEquals": {"aws:PrincipalOrgID": organization_id}},
                        effect=aws_iam.Effect.ALLOW,
                        principals=[aws_iam.AnyPrincipal()],
                        resources=["*"],
                    )
                )
            ],
        )

        aws_cdk.CfnOutput(
            self,
            f"KeyArn{id_suffix}",
            description="The ARN of the KMS key",
            value=self.__key.key.key_arn,
        ).override_logical_id(f"KeyArn{id_suffix}")

    @property
    def key(self) -> key.Key:
        return self.__key
