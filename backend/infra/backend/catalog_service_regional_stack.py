import aws_cdk
import constructs
from aws_cdk import aws_iam, aws_sns

from infra import config
from infra.constructs.sns import topic


class CatalogServiceRegionalStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        organization_id: str,
        web_app_account_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # SNS topic for service catalog notifications
        self.__catalog_srv_topic = topic.Topic(
            self,
            "CatalogServiceNotificationsTopic",
            create_key=True,
            topic_name=app_config.format_resource_name_with_region("notifications"),
            key_permissions=[
                lambda lambda_f: lambda_f.add_to_resource_policy(
                    aws_iam.PolicyStatement(
                        actions=[
                            "kms:Decrypt",
                            "kms:GenerateDataKey",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        principals=[aws_iam.AnyPrincipal()],
                        resources=["*"],
                        conditions={"StringEquals": {"aws:PrincipalOrgID": organization_id}},
                    ),
                ),
            ],
        )
        self.__catalog_srv_topic.topic.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "sns:Publish",
                ],
                effect=aws_iam.Effect.ALLOW,
                principals=[aws_iam.AnyPrincipal()],
                conditions={"StringEquals": {"aws:PrincipalOrgID": organization_id}},
                resources=[self.__catalog_srv_topic.topic.topic_arn],
            )
        )
        self.__catalog_srv_topic.topic.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=["sns:Subscribe"],
                effect=aws_iam.Effect.ALLOW,
                principals=[aws_iam.AccountPrincipal(web_app_account_id)],
                resources=[self.__catalog_srv_topic.topic.topic_arn],
            )
        )

    @property
    def topic(self) -> aws_sns.Topic:
        return self.__catalog_srv_topic.topic
