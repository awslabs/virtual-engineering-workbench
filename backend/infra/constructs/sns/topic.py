from typing import Callable, Optional, Sequence

import constructs
from aws_cdk import aws_iam, aws_kms, aws_sns

from infra.constructs.kms import key


class Topic(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        topic_name: str,
        create_key: Optional[bool] = False,
        key_permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        master_key: Optional[aws_kms.IKey] = None,
        topic_permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
    ) -> None:
        super().__init__(scope, id)

        self.__key = None
        if create_key:
            self.__key = key.Key(
                self,
                "Key",
                alias=f"{topic_name}-key",
                description=f"Key used to encrypt/decrypt {topic_name} messages.",
                permissions=key_permissions,
            )
            master_key = self.__key.key
        self.__topic = aws_sns.Topic(
            self,
            "Topic",
            master_key=master_key,
            topic_name=topic_name,
        )

        for permission in topic_permissions:
            permission(self.__topic)
        self.__topic.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "sns:Publish",
                ],
                conditions={
                    "Bool": {"aws:SecureTransport": "false"},
                },
                effect=aws_iam.Effect.DENY,
                principals=[
                    aws_iam.StarPrincipal(),
                ],
                resources=[self.__topic.topic_arn],
            )
        )

    @property
    def key(self) -> Optional[key.Key]:
        return self.__key

    @property
    def topic(self) -> aws_sns.Topic:
        return self.__topic
