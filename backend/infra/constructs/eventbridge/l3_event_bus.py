import typing

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_events, aws_events_targets, aws_iam, aws_lambda, aws_sqs, aws_ssm, aws_stepfunctions

from infra import config
from infra.constructs.eventbridge.eb_upsert import EB_UPSERT_SSM_PARAM_NAME


class EventBus(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        event_bus_name: str,
    ) -> None:
        super().__init__(scope, id)

        self._app_config = app_config

        service_token = aws_ssm.StringParameter.from_string_parameter_attributes(
            self,
            "service-token",
            parameter_name=EB_UPSERT_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        self._eb = aws_cdk.CustomResource(
            self, "eb-upsert-param", service_token=service_token, properties={"Name": event_bus_name}
        )

        self._event_bus = aws_events.EventBus.from_event_bus_arn(
            self, "eb", event_bus_arn=self._eb.get_att_string("EventBusArn")
        )

    def subscribe_to_events(
        self,
        name: str,
        events: typing.List[str],
        lambda_function: aws_lambda.IFunction | aws_lambda.IAlias = None,
        state_machine: aws_stepfunctions.StateMachine = None,
        event_detail_match: typing.Mapping[str, typing.Any] | None = None,
    ):
        if lambda_function:
            self.add_rule_with_lambda_target(
                name=name,
                event_pattern=aws_events.EventPattern(
                    detail_type=aws_events.Match.any_of(*[aws_events.Match.exact_string(evt) for evt in events]),
                    detail=event_detail_match,
                ),
                lambda_function=lambda_function,
                duration_in_minutes=720,
                max_retries=3,
            )
        if state_machine:
            self.add_rule_with_sfn_target(
                name=name,
                event_pattern=aws_events.EventPattern(
                    detail_type=aws_events.Match.any_of(*[aws_events.Match.exact_string(evt) for evt in events]),
                    detail=event_detail_match,
                ),
                state_machine=state_machine,
                duration_in_minutes=720,
                max_retries=3,
            )

    def add_rule_with_lambda_target(
        self,
        name: str,
        event_pattern: aws_events.EventPattern,
        lambda_function: aws_lambda.IFunction | aws_lambda.IAlias,
        duration_in_minutes: int,
        max_retries: int,
    ):
        rule = aws_events.Rule(
            self,
            id=name,
            event_bus=self._event_bus,
            event_pattern=event_pattern,
            rule_name=self._app_config.format_resource_name(name),
        )

        dlq = self.get_dlq(name=name)

        rule.add_target(
            target=aws_events_targets.LambdaFunction(
                handler=lambda_function,
                dead_letter_queue=dlq,
                max_event_age=aws_cdk.Duration.minutes(duration_in_minutes),
                retry_attempts=max_retries,
            )
        )

    def add_rule_with_sfn_target(
        self,
        name: str,
        event_pattern: aws_events.EventPattern,
        state_machine: aws_stepfunctions.StateMachine,
        duration_in_minutes: int,
        max_retries: int,
    ):
        rule: aws_events.Rule = aws_events.Rule(
            self,
            id=name,
            event_bus=self._event_bus,
            event_pattern=event_pattern,
            rule_name=self._app_config.format_resource_name(name),
        )

        dlq = self.get_dlq(name=name)

        rule.add_target(
            target=aws_events_targets.SfnStateMachine(
                machine=state_machine,
                dead_letter_queue=dlq,
                max_event_age=aws_cdk.Duration.minutes(duration_in_minutes),
                retry_attempts=max_retries,
            )
        )

    def get_dlq(self, name: str) -> aws_sqs.Queue:
        dlq: aws_sqs.Queue = aws_sqs.Queue(
            self,
            id=f"{name}-dlq",
            queue_name=self._app_config.format_resource_name(f"{name}-dlq"),
            encryption=aws_sqs.QueueEncryption.KMS_MANAGED,
        )

        dlq.add_to_resource_policy(
            aws_iam.PolicyStatement(
                sid="Enforce TLS for all principals",
                effect=aws_iam.Effect.DENY,
                principals=[
                    aws_iam.AnyPrincipal(),
                ],
                actions=[
                    "sqs:*",
                ],
                conditions={
                    "Bool": {"aws:secureTransport": "false"},
                },
                resources=[dlq.queue_arn],
            )
        )

        # cdk_nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=dlq,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-SQS3",
                    reason="This is already a dead-letter-queue.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-SQS4",
                    reason="False positive: resource policy denies non-tls encrypted traffic.",
                ),
            ],
        )

        return dlq

    @property
    def event_bus(self):
        return self._event_bus


def from_bounded_context(
    scope, id, app_config: config.AppConfig, bounded_context_name: str, event_bus_name: str = "domain-events"
) -> EventBus:
    """
    Creates or gets en EventBridge event bus from another component (bounded context)
    """
    eb_name = app_config.format_resource_name_with_component(component_name=bounded_context_name, name=event_bus_name)

    return EventBus(
        scope,
        id,
        app_config=app_config,
        event_bus_name=eb_name,
    )


def for_self(scope, id, app_config: config.AppConfig, event_bus_name: str = "domain-events") -> EventBus:
    """
    Creates or gets an EventBridge event bus for a component from app_config.
    """
    return from_bounded_context(
        scope, id, app_config=app_config, bounded_context_name=app_config.component_name, event_bus_name=event_bus_name
    )
