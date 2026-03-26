from typing import Callable, Optional, Sequence

import cdk_nag
import constructs
from aws_cdk import (
    Duration,
    Stack,
    aws_events,
    aws_iam,
    aws_kms,
    aws_pipes_alpha,
    aws_pipes_sources_alpha,
    aws_pipes_targets_alpha,
    aws_sns,
    aws_sns_subscriptions,
    aws_sqs,
)

from infra.constructs.kms import key
from infra.constructs.logs import log_group
from infra.constructs.sqs import queue


class TopicToEventBusPipe(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        event_bus: aws_events.IEventBus,
        pipe_name: str,
        topics: list[aws_sns.ITopic],
        create_key: Optional[bool] = False,
        detail_type: Optional[str] = None,
        description: Optional[str] = None,
        desired_state: Optional[aws_pipes_alpha.DesiredState] = aws_pipes_alpha.DesiredState.RUNNING,
        kms_key: Optional[aws_kms.IKey] = None,
        log_include_execution_data: Optional[Sequence[aws_pipes_alpha.IncludeExecutionData]] = None,
        log_level: Optional[aws_pipes_alpha.LogLevel] = aws_pipes_alpha.LogLevel.ERROR,
        input_transformation: Optional[aws_pipes_alpha.IInputTransformation] = None,
        max_receive_count: Optional[int] = 10,
        permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        resources: Optional[Sequence[str]] = None,
        source: Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)

        self.__key = None
        if create_key:
            self.__key = key.Key(
                self,
                "Key",
                alias=f"{pipe_name}-key",
                description=f"Key used to encrypt/decrypt {pipe_name} logs and messages.",
                permissions=[
                    lambda lambda_f: lambda_f.add_to_resource_policy(
                        aws_iam.PolicyStatement(
                            actions=[
                                "kms:Decrypt",
                                "kms:GenerateDataKey",
                            ],
                            conditions={
                                "StringLike": {
                                    "kms:EncryptionContext:SourceArn": Stack.of(self).format_arn(
                                        account=Stack.of(self).account,
                                        partition=Stack.of(self).partition,
                                        region=Stack.of(self).region,
                                        resource="*",
                                        service="logs",
                                    ),
                                },
                            },
                            effect=aws_iam.Effect.ALLOW,
                            principals=[
                                aws_iam.ServicePrincipal(f"delivery.logs.{Stack.of(self).url_suffix}"),
                            ],
                            resources=[
                                "*",
                            ],
                        ),
                    ),
                ],
            )
            kms_key = self.__key.key
        self.__log_group = log_group.LogGroup(
            self,
            "LogGroup",
            encryption_key=kms_key,
            log_group_name=f"/pipes/{pipe_name}",
        )
        self.__dead_letter_queue = queue.Queue(
            self,
            "DeadLetterQueue",
            data_key_reuse=Duration.hours(1),
            encryption=aws_sqs.QueueEncryption.KMS if kms_key else aws_sqs.QueueEncryption.KMS_MANAGED,
            encryption_master_key=kms_key,
            queue_name=f"{pipe_name}-queue-dlq",
            receive_message_wait_time=Duration.seconds(20),
            retention_period=Duration.days(14),
        )
        self.__queue = queue.Queue(
            self,
            "Queue",
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                max_receive_count=max_receive_count,
                queue=self.__dead_letter_queue.queue,
            ),
            data_key_reuse=Duration.hours(1),
            encryption=aws_sqs.QueueEncryption.KMS if kms_key else aws_sqs.QueueEncryption.KMS_MANAGED,
            encryption_master_key=kms_key,
            queue_name=f"{pipe_name}-queue",
            receive_message_wait_time=Duration.seconds(20),
        )
        # TODO: switch to a customer managed key when available in the construct
        self.__pipe = aws_pipes_alpha.Pipe(
            self,
            "Pipe",
            description=description,
            desired_state=desired_state,
            log_destinations=[
                aws_pipes_alpha.CloudwatchLogsLogDestination(log_group=self.__log_group.log_group),
            ],
            log_include_execution_data=log_include_execution_data,
            log_level=log_level,
            pipe_name=pipe_name,
            source=aws_pipes_sources_alpha.SqsSource(queue=self.__queue.queue),
            target=aws_pipes_targets_alpha.EventBridgeTarget(
                detail_type=detail_type,
                event_bus=event_bus,
                input_transformation=input_transformation,
                resources=resources,
                source=source,
            ),
        )

        for permission in permissions:
            permission(self.__pipe.pipe_role)
        for topic in topics:
            topic.add_subscription(aws_sns_subscriptions.SqsSubscription(self.__queue.queue))
        if kms_key:
            kms_key.add_to_resource_policy(
                aws_iam.PolicyStatement(
                    actions=[
                        "kms:GenerateDataKey",
                    ],
                    conditions={
                        "StringLike": {
                            "kms:EncryptionContext:SourceArn": Stack.of(self).format_arn(
                                account=Stack.of(self).account,
                                partition=Stack.of(self).partition,
                                region=Stack.of(self).region,
                                resource="*",
                                service="logs",
                            ),
                        },
                    },
                    effect=aws_iam.Effect.ALLOW,
                    principals=[
                        self.__pipe.pipe_role,
                    ],
                    resources=[
                        "*",
                    ],
                ),
            )
            self.__pipe.pipe_role.add_to_policy(
                aws_iam.PolicyStatement(
                    actions=[
                        "kms:GenerateDataKey",
                    ],
                    conditions={
                        "StringLike": {
                            "kms:EncryptionContext:SourceArn": Stack.of(self).format_arn(
                                account=Stack.of(self).account,
                                partition=Stack.of(self).partition,
                                region=Stack.of(self).region,
                                resource="*",
                                service="logs",
                            ),
                        },
                    },
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        kms_key.key_arn,
                    ],
                ),
            )
        self.__apply_nag_suppressions()

    @property
    def dead_letter_queue(self) -> queue.Queue:
        return self.__dead_letter_queue

    @property
    def log_group(self) -> log_group.LogGroup:
        return self.__log_group

    @property
    def key(self) -> Optional[key.Key]:
        return self.__key

    @property
    def pipe(self) -> aws_pipes_alpha.Pipe:
        return self.__pipe

    @property
    def queue(self) -> queue.Queue:
        return self.__queue

    def __apply_nag_suppressions(self):
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.log_group.log_group,
            [
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    reason="The log group will always be encrypted with a KMS key (this is a false positive).",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupRetentionPeriod",
                    reason="The log group retention period is set by default to aws_logs.RetentionDays.INFINITE.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    reason="The log group will always be encrypted with a KMS key (this is a false positive).",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupRetentionPeriod",
                    reason="The log group retention period is set by default to aws_logs.RetentionDays.INFINITE.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    reason="The log group will always be encrypted with a KMS key (this is a false positive).",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupRetentionPeriod",
                    reason="The log group retention period is set by default to aws_logs.RetentionDays.INFINITE.",
                ),
            ],
        )

        role_policy = [_ for _ in self.pipe.pipe_role.node.children if isinstance(_, aws_iam.Policy)][0]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            role_policy,
            [
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
            ],
        )
