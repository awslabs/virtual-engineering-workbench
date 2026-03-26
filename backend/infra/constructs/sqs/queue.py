from typing import Any, Callable, Optional, Sequence, Union

import constructs
from aws_cdk import Duration, RemovalPolicy, aws_iam, aws_kms, aws_sqs

from infra.constructs.kms import key


class Queue(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        queue_name: str,
        create_key: Optional[bool] = False,
        data_key_reuse: Optional[Duration] = Duration.minutes(5),
        dead_letter_queue: Optional[Union[aws_sqs.DeadLetterQueue, dict[str, Any]]] = None,
        encryption: Optional[aws_sqs.QueueEncryption] = aws_sqs.QueueEncryption.KMS_MANAGED,
        encryption_master_key: Optional[aws_kms.IKey] = None,
        key_permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        queue_permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        redrive_allow_policy: Optional[Union[aws_sqs.RedriveAllowPolicy, dict[str, Any]]] = None,
        receive_message_wait_time: Optional[Duration] = Duration.seconds(0),
        removal_policy: Optional[RemovalPolicy] = RemovalPolicy.DESTROY,
        retention_period: Optional[Duration] = Duration.days(4),
    ) -> None:
        super().__init__(scope, id)

        self.__key = None
        if create_key:
            self.__key = key.Key(
                self,
                "Key",
                alias=f"{queue_name}-key",
                description=f"Key used to encrypt/decrypt {queue_name} messages.",
                permissions=key_permissions,
            )
            encryption_master_key = self.__key.key
        self.__queue = aws_sqs.Queue(
            self,
            "Queue",
            data_key_reuse=data_key_reuse,
            dead_letter_queue=dead_letter_queue,
            encryption=encryption,
            encryption_master_key=encryption_master_key,
            enforce_ssl=True,
            queue_name=queue_name,
            redrive_allow_policy=redrive_allow_policy,
            receive_message_wait_time=receive_message_wait_time,
            removal_policy=removal_policy,
            retention_period=retention_period,
        )

        for permission in queue_permissions:
            permission(self.__queue)

    @property
    def key(self) -> Optional[key.Key]:
        return self.__key

    @property
    def queue(self) -> aws_sqs.Queue:
        return self.__queue
