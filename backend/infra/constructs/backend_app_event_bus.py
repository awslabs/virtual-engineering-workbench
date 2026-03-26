from typing import Optional, Sequence

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_events, aws_events_targets, aws_iam, aws_lambda, aws_logs, aws_sqs

from infra import config
from infra.constructs.eventbridge import l3_event_bus


class BackendAppEventBus(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        event_bus_name: str = "domain-events",
    ) -> None:
        super().__init__(scope, id)

        eb = l3_event_bus.for_self(self, "event-bus", app_config=app_config, event_bus_name=event_bus_name)

        self._bus = eb.event_bus
        self._l3_bus = eb

        self._app_config = app_config

        log_group_name = f"/events/{app_config.format_resource_name(event_bus_name)}"

        self._log_group = aws_logs.LogGroup(
            self,
            "event-bus-log",
            log_group_name=log_group_name,
            removal_policy=(
                aws_cdk.RemovalPolicy.DESTROY if app_config.environment == "dev" else aws_cdk.RemovalPolicy.RETAIN
            ),
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        rule = aws_events.Rule(
            self,
            "log-rule",
            event_bus=self._bus,
            rule_name=self._app_config.format_resource_name(f"{event_bus_name}-log"),
            event_pattern=aws_events.EventPattern(region=[aws_cdk.Stack.of(self).region]),
        )

        rule_cfn = rule.node.default_child

        rule_cfn.targets = [
            aws_events.CfnRule.TargetProperty(
                arn=aws_cdk.Stack.of(self).format_arn(
                    arn_format=aws_cdk.ArnFormat.COLON_RESOURCE_NAME,
                    service="logs",
                    resource="log-group",
                    resource_name=self._log_group.log_group_name,
                ),
                id="log-to-cloudwatch",
            )
        ]

        # log group suppression
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._log_group,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
            ],
        )

    def allow_publish_from_account(self, account_id: str):
        aws_events.CfnEventBusPolicy(
            self,
            "event-bus-resource-policy",
            statement_id=self._bus.event_bus_name,
            action="events:PutEvents",
            event_bus_name=self._bus.event_bus_name,
            principal=account_id,
        )

    def allow_publish_from_organization(self, organization_id: str):
        aws_events.CfnEventBusPolicy(
            self,
            "event-bus-resource-policy-org",
            statement_id=f"{self._bus.event_bus_name}-org",
            action="events:PutEvents",
            event_bus_name=self._bus.event_bus_name,
            principal="*",
            condition=aws_events.CfnEventBusPolicy.ConditionProperty(
                key="aws:PrincipalOrgID", type="StringEquals", value=organization_id
            ),
        )

    def route_to_event_bus(
        self,
        event_bus_arn: str,
        rule_name: str,
        event_name: str,
        detail_type: Optional[Sequence[str]] = None,
        source: Optional[Sequence[str]] = None,
    ):
        event_bus_role = aws_iam.Role(
            self,
            f"EventsRole{event_name}",
            assumed_by=aws_iam.ServicePrincipal("events.amazonaws.com"),
            role_name=f"EventBusForwarding-{event_name}",
            path="/VirtualWorkbench/",
        )

        rule = aws_events.Rule(
            self,
            f"{rule_name}-rule",
            rule_name=self._app_config.format_resource_name(rule_name),
            event_pattern=aws_events.EventPattern(
                detail_type=detail_type if detail_type else [event_name],
                source=source if source else [self._app_config.bounded_context_name],
            ),
            event_bus=self._bus,
        )

        dlq = aws_sqs.Queue(
            self,
            f"{rule_name}-dlq",
            queue_name=self._app_config.format_resource_name(f"{rule_name}-dlq"),
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
                    "Bool": {"aws:SecureTransport": "false"},
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
            ],
        )

        rule.add_target(
            aws_events_targets.EventBus(
                aws_events.EventBus.from_event_bus_arn(self, f"{rule_name}-target", event_bus_arn),
                dead_letter_queue=dlq,
                role=event_bus_role,
            )
        )

        # Following gymnastics is to suppres a cdk_nag error that is generated by CDK constructs.
        default_policy = [p for p in event_bus_role.node.children if isinstance(p, aws_iam.Policy)][0]
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=default_policy,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auti-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auti-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auti-generated by CDK.",
                ),
            ],
        )

        return self

    def grant_put_events_to(self, grantee: aws_iam.IGrantable):
        self._bus.grant_put_events_to(grantee)
        return self

    def add_rule_with_lambda_target(
        self,
        name: str,
        event_pattern: aws_events.EventPattern,
        lambda_function: aws_lambda.IFunction,
        duration_in_minutes: int,
        max_retries: int,
        target_input_transformation: aws_events.RuleTargetInput | None = None,
    ):
        rule = aws_events.Rule(
            self,
            id=name,
            event_bus=self._bus,
            event_pattern=event_pattern,
            rule_name=self._app_config.format_resource_name(name),
        )

        dlq = aws_sqs.Queue(
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
                    "Bool": {"aws:SecureTransport": "false"},
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
            ],
        )

        rule.add_target(
            target=aws_events_targets.LambdaFunction(
                handler=lambda_function,
                dead_letter_queue=dlq,
                max_event_age=aws_cdk.Duration.minutes(duration_in_minutes),
                retry_attempts=max_retries,
                event=target_input_transformation if target_input_transformation else None,
            ),
        )

    @property
    def event_bus_arn(self):
        return self._bus.event_bus_arn

    @property
    def event_bus_log_arn(self):
        return self._log_group.log_group_arn

    @property
    def event_bus(self) -> aws_events.EventBus:
        return self._bus

    @property
    def l3_event_bus(self) -> l3_event_bus.EventBus:
        return self._l3_bus
