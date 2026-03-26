import enum
import inspect
import pkgutil
import typing

import aws_cdk
import cdk_nag
from aws_cdk import aws_apigateway
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_stepfunctions as sfn

from app.shared.adapters.message_bus import command_bus, message_bus
from infra import config
from infra.constructs import backend_app_entrypoints

if typing.TYPE_CHECKING:
    from aws_cdk import aws_glue_alpha as glue_alpha


class OpsDashboardWidgetColor(enum.StrEnum):
    Red = "#d62728"
    Blue = "#1f77b4"
    Green = "#2ca02c"
    Orange = "#ff7f0e"


OPS_DASHBOARD_WIDGET_HEIGHT = 5
OPS_DASHBOARD_WIDGET_WIDTH_QUARTER = 6
OPS_DASHBOARD_TOTAL_WIDTH = 24


class OpsMonitoringBuilder:
    def __init__(
        self,
        scope,
        dashboard_name: str,
        namespace: str,
        service: str,
        app_config: config.AppConfig,
    ):
        self._scope = scope
        self._dashboard_name = dashboard_name
        self._namespace = namespace
        self._service = service
        self._widgets: list[cloudwatch.IWidget] = []
        self._alarms: list[cloudwatch.IAlarm] = []
        self._app_config = app_config

    def with_lambda_functions(
        self, app_entry_points: typing.Iterable[backend_app_entrypoints.AppEntryFunctionsAttributes]
    ) -> "OpsMonitoringBuilder":
        app_entry_list = list(app_entry_points)
        self._widgets.extend(_create_lambda_widgets(app_entry_list))
        self._alarms.extend(_create_lambda_alarms(self._scope, app_entry_list))
        self._widgets.extend(_create_durable_lambda_widgets(app_entry_list))
        self._alarms.extend(_create_durable_lambda_alarms(self._scope, app_entry_list))
        return self

    def with_dynamodb_table(self, table: aws_dynamodb.ITable) -> "OpsMonitoringBuilder":
        self._widgets.extend(_create_dynamodb_widgets(table))
        return self

    def with_api_gateway(self, gw: aws_apigateway.IRestApi) -> "OpsMonitoringBuilder":
        self._widgets.extend(_create_api_widgets(gw, self._app_config))
        self._alarms.extend(_create_api_alarms(self._scope, gw))
        return self

    def with_s3_replication(
        self,
        bucket: s3.IBucket,
        search_regions: list[str],
        replication_time_mins: int,
        metric_search_expression_fn: typing.Callable,
    ) -> "OpsMonitoringBuilder":
        self._widgets.append(
            _create_s3_replication_widget(bucket, search_regions, replication_time_mins, metric_search_expression_fn)
        )
        return self

    def with_s3_buckets(self, buckets: list[s3.IBucket]) -> "OpsMonitoringBuilder":
        self._widgets.append(_create_s3_buckets_widget(buckets))
        return self

    def with_glue_etl_job(self, job: "glue_alpha.IJob", period_hours: int) -> "OpsMonitoringBuilder":
        self._widgets.extend(_create_glue_etl_widgets(job, period_hours))
        self._alarms.append(_create_glue_etl_alarm(self._scope, job))
        return self

    def with_step_functions(self, state_machines: list[sfn.StateMachine]) -> "OpsMonitoringBuilder":
        self._widgets.append(_create_step_functions_widget(state_machines))
        self._alarms.extend(_create_step_functions_alarms(self._scope, state_machines))
        return self

    def with_command_monitoring(
        self, domain_module: typing.Any, critical_commands: set[str] | None = None
    ) -> "OpsMonitoringBuilder":
        critical_commands = critical_commands or set()
        command_list = _discover_classes(domain_module, command_bus.Command, critical_commands)

        self._widgets.extend(_create_command_widgets(self._namespace, self._service, command_list))
        self._alarms.extend(
            _create_command_alarms(
                self._scope, self._namespace, self._service, command_list, self._app_config.format_resource_name
            )
        )

        return self

    def with_domain_event_monitoring(
        self, domain_module: typing.Any, critical_events: set[str] | None = None
    ) -> "OpsMonitoringBuilder":
        critical_events = critical_events or set()
        event_list = _discover_classes(domain_module, message_bus.Message, critical_events)

        self._widgets.extend(_create_domain_event_widgets(self._namespace, self._service, event_list))
        self._alarms.extend(
            _create_domain_event_alarms(
                self._scope, self._namespace, self._service, event_list, self._app_config.format_resource_name
            )
        )

        return self

    def build(self) -> cloudwatch.Dashboard:
        # Create composite alarm if there are alarms and prepend it to the list
        if self._alarms:
            composite_alarm = cloudwatch.CompositeAlarm(
                self._scope,
                "SystemHealthCompositeAlarm",
                alarm_rule=cloudwatch.AlarmRule.any_of(*self._alarms),
                composite_alarm_name=self._app_config.format_resource_name("system-health"),
                alarm_description="System health - triggers if any component alarm is in ALARM state",
            )

            composite_alarm.add_alarm_action(cloudwatch_actions.SnsAction(self.__build_topic()))

            self._alarms.insert(0, composite_alarm)

        for alarm in self._alarms:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=alarm,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R4-CloudWatchAlarmAction",
                        reason="SNS alarm action is added to the composite alarm only.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R5-CloudWatchAlarmAction",
                        reason="SNS alarm action is added to the composite alarm only.",
                    ),
                ],
                apply_to_children=True,
            )

        dashboard = cloudwatch.Dashboard(
            self._scope,
            "OpsDashboard",
            dashboard_name=self._dashboard_name,
            start="-P1W",
            widgets=_layout_dashboard_widgets(self._widgets, self._alarms),
        )

        return dashboard

    def __build_topic(self) -> sns.Topic:
        key = kms.Key(
            self._scope,
            "SNSKey",
            description=f"SNS alarm topic KMS key to monitor {aws_cdk.Stack.of(self._scope).stack_name}",
            enable_key_rotation=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            pending_window=aws_cdk.Duration.days(10),
        )

        topic = sns.Topic(
            self._scope,
            "MonitoringAlarmsTopic",
            display_name=self._app_config.format_resource_name("monitoring-alarms"),
            master_key=key,
        )

        topic.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
                resources=[topic.topic_arn],
            )
        )

        aws_cdk.CfnOutput(self._scope, id="MonitoringAlarmsTopicName", value=topic.topic_name).override_logical_id(
            "MonitoringAlarmsTopicName"
        )

        return topic


def _create_lambda_widgets(
    app_entry_points: typing.Iterable[backend_app_entrypoints.AppEntryFunctionsAttributes],
) -> list[cloudwatch.IWidget]:
    def lambda_metric(function_name: str, metric_name: str, period: aws_cdk.Duration | None = None):
        return cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name=metric_name,
            dimensions_map={"FunctionName": function_name},
            period=period,
        )

    return [
        cloudwatch.GraphWidget(
            left=[lambda_metric(app_entry.function.function_name, "Invocations") for app_entry in app_entry_points],
            title="Lambda Invocations",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        ),
        cloudwatch.GraphWidget(
            left=[lambda_metric(app_entry.function.function_name, "Duration") for app_entry in app_entry_points],
            title="Lambda Duration",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="p95",
            period=aws_cdk.Duration.minutes(5),
        ),
        cloudwatch.GraphWidget(
            left=[lambda_metric(app_entry.function.function_name, "Errors") for app_entry in app_entry_points],
            right=[lambda_metric(app_entry.function.function_name, "Throttles") for app_entry in app_entry_points],
            title="Errors <- Lambda -> Throttles",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        ),
    ]


def _create_lambda_alarms(
    scope, app_entry_points: typing.Iterable[backend_app_entrypoints.AppEntryFunctionsAttributes]
) -> list[cloudwatch.IAlarm]:
    def lambda_metric(function_name: str, metric_name: str, period: aws_cdk.Duration | None = None):
        return cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name=metric_name,
            dimensions_map={"FunctionName": function_name},
            period=period,
        )

    alarms = []
    for app_entry in app_entry_points:
        alarms.append(
            cloudwatch.Alarm(
                scope,
                f"AlarmLambdaError{app_entry.app_name}",
                metric=lambda_metric(app_entry.function.function_name, "Errors", period=aws_cdk.Duration.minutes(5)),
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                threshold=1,
                evaluation_periods=3,
                datapoints_to_alarm=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_name=f"{app_entry.function.function_name}-errors",
                alarm_description=f"Alarm for Lambda errors in {app_entry.function.function_name}",
            )
        )
        alarms.append(
            cloudwatch.Alarm(
                scope,
                f"AlarmLambdaThrottle{app_entry.app_name}",
                metric=lambda_metric(app_entry.function.function_name, "Throttles", period=aws_cdk.Duration.minutes(5)),
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                threshold=1,
                evaluation_periods=3,
                datapoints_to_alarm=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_name=f"{app_entry.function.function_name}-throttles",
                alarm_description=f"Alarm for Lambda throttles in {app_entry.function.function_name}",
            )
        )
    return alarms


def _create_durable_lambda_widgets(
    app_entry_points: typing.Iterable[backend_app_entrypoints.AppEntryFunctionsAttributes],
) -> list[cloudwatch.IWidget]:
    durable_function_names = [
        entry.function.function_name
        for entry in app_entry_points
        if hasattr(cfn_func := entry.function.node.default_child, "durable_config") and cfn_func.durable_config
    ]

    if not durable_function_names:
        return []

    def durable_metric(function_name: str, metric_name: str, color: OpsDashboardWidgetColor | None = None):
        return cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name=metric_name,
            dimensions_map={"FunctionName": function_name},
            color=color,
            label=f"{function_name} {metric_name}",
        )

    return [
        cloudwatch.GraphWidget(
            left=[
                durable_metric(fn, "DurableExecutionSucceeded", OpsDashboardWidgetColor.Green)
                for fn in durable_function_names
            ],
            right=[
                *[
                    durable_metric(fn, "DurableExecutionFailed", OpsDashboardWidgetColor.Red)
                    for fn in durable_function_names
                ],
                *[
                    durable_metric(fn, "DurableExecutionTimedOut", OpsDashboardWidgetColor.Orange)
                    for fn in durable_function_names
                ],
            ],
            title="Succeeded <- Durable Lambda -> Failed/TimedOut",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        ),
        cloudwatch.GraphWidget(
            left=[durable_metric(fn, "DurableExecutionDuration") for fn in durable_function_names],
            title="Durable Lambda Duration",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="p95",
            period=aws_cdk.Duration.minutes(5),
        ),
    ]


def _create_durable_lambda_alarms(
    scope, app_entry_points: typing.Iterable[backend_app_entrypoints.AppEntryFunctionsAttributes]
) -> list[cloudwatch.IAlarm]:
    durable_entries = [
        entry
        for entry in app_entry_points
        if hasattr(cfn_func := entry.function.node.default_child, "durable_config") and cfn_func.durable_config
    ]

    if not durable_entries:
        return []

    def durable_metric(function_name: str, metric_name: str):
        return cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name=metric_name,
            dimensions_map={"FunctionName": function_name},
            period=aws_cdk.Duration.minutes(5),
        )

    alarms = []
    for entry in durable_entries:
        alarms.extend(
            [
                cloudwatch.Alarm(
                    scope,
                    f"AlarmDurableLambdaFailed{entry.app_name}",
                    metric=durable_metric(entry.function.function_name, "DurableExecutionFailed"),
                    treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                    threshold=1,
                    evaluation_periods=1,
                    datapoints_to_alarm=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                    alarm_name=f"{entry.function.function_name}-durable-failed",
                    alarm_description=f"Alarm for durable execution failures in {entry.function.function_name}",
                ),
                cloudwatch.Alarm(
                    scope,
                    f"AlarmDurableLambdaTimedOut{entry.app_name}",
                    metric=durable_metric(entry.function.function_name, "DurableExecutionTimedOut"),
                    treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                    threshold=1,
                    evaluation_periods=1,
                    datapoints_to_alarm=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                    alarm_name=f"{entry.function.function_name}-durable-timedout",
                    alarm_description=f"Alarm for durable execution timeouts in {entry.function.function_name}",
                ),
            ]
        )

    return alarms


def _create_dynamodb_widgets(table: aws_dynamodb.ITable) -> list[cloudwatch.IWidget]:
    def ddb_metrics_search_expression(metric_name: str, operation: str):
        return " ".join(
            [
                "{AWS/DynamoDB,TableName,StreamLabel,Operation}",
                f'TableName="{table.table_name}"',
                f'MetricName="{metric_name}"',
                f'Operation="{operation}"',
            ]
        )

    def metric_search_expression(expression: str, aggregator: str, time: int):
        return ", ".join([f"SEARCH('{expression}'", f"'{aggregator}'", f"{time})"])

    def ddb_expression(metric_name: str, operation: str):
        return cloudwatch.MathExpression(
            expression=metric_search_expression(
                expression=ddb_metrics_search_expression(metric_name, operation),
                aggregator="Sum",
                time=5 * 60,
            ),
            label="",
        )

    def ddb_metric(metric_name: str):
        return cloudwatch.Metric(
            namespace="AWS/DynamoDB",
            metric_name=metric_name,
            dimensions_map={"TableName": table.table_name},
        )

    # Common DynamoDB operations
    operations = [
        "GetItem",
        "PutItem",
        "UpdateItem",
        "DeleteItem",
        "Query",
        "Scan",
        "BatchGetItem",
        "BatchWriteItem",
        "TransactWriteItem",
    ]

    return [
        cloudwatch.GraphWidget(
            left=[ddb_metric("ConsumedWriteCapacityUnits"), ddb_metric("ConsumedReadCapacityUnits")],
            right=[ddb_expression("ReturnedRecordsCount", "GetRecords")],
            title="RCU/WCU <- DynamoDB -> Stream Records",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        ),
        cloudwatch.GraphWidget(
            left=[
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="SuccessfulRequestLatency",
                    dimensions_map={"TableName": table.table_name, "Operation": op},
                    label=op,
                )
                for op in operations
            ],
            title="DynamoDB Request Latency",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="p99",
            period=aws_cdk.Duration.minutes(5),
        ),
    ]


def _create_api_widgets(gw: aws_apigateway.IRestApi, app_config: config.BaseConfig) -> list[cloudwatch.IWidget]:
    # Extract name by removing organization and application prefixes and environment suffix
    org_prefix = app_config.get_organization_prefix()
    app_prefix = app_config.get_application_prefix()
    env = app_config.environment

    # Remove prefix pattern: {org}-{app}-
    prefix_to_remove = f"{org_prefix}-{app_prefix}-"
    # Remove suffix pattern: -{env}
    suffix_to_remove = f"-{env}"

    display_name = gw.rest_api_name
    if display_name.startswith(prefix_to_remove):
        display_name = display_name[len(prefix_to_remove) :]
    if display_name.endswith(suffix_to_remove):
        display_name = display_name[: -len(suffix_to_remove)]

    def gw_metric(
        metric_name: str, color: OpsDashboardWidgetColor | None = None, period: aws_cdk.Duration | None = None
    ):
        return cloudwatch.Metric(
            namespace="AWS/ApiGateway",
            metric_name=metric_name,
            dimensions_map={"ApiName": gw.rest_api_name},
            color=color,
            period=period,
        )

    return [
        cloudwatch.GraphWidget(
            left=[gw_metric("Count", OpsDashboardWidgetColor.Blue)],
            right=[
                gw_metric("4XXError", OpsDashboardWidgetColor.Orange),
                gw_metric("5XXError", OpsDashboardWidgetColor.Red),
            ],
            title=f"Requests <- {display_name} -> Errors",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        ),
        cloudwatch.GraphWidget(
            left=[gw_metric("Latency")],
            title=f"{display_name} latency",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="p95",
            period=aws_cdk.Duration.minutes(5),
        ),
    ]


def _create_api_alarms(scope, gw: aws_apigateway.IRestApi) -> list[cloudwatch.IAlarm]:
    def gw_metric(
        metric_name: str, color: OpsDashboardWidgetColor | None = None, period: aws_cdk.Duration | None = None
    ):
        return cloudwatch.Metric(
            namespace="AWS/ApiGateway",
            metric_name=metric_name,
            dimensions_map={"ApiName": gw.rest_api_name},
            color=color,
            period=period,
        )

    return [
        cloudwatch.Alarm(
            scope,
            f"AlarmAPI5XX{gw.rest_api_name}",
            metric=gw_metric("5XXError", period=aws_cdk.Duration.minutes(5)),
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            threshold=1,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_name=f"{gw.rest_api_name}-5xx",
            alarm_description=f"Alarm for API 5xx errors in {gw.rest_api_name}",
        )
    ]


def _create_s3_replication_widget(
    bucket: s3.IBucket,
    search_regions: list[str],
    replication_time_mins: int,
    metric_search_expression_fn: typing.Callable,
) -> cloudwatch.IWidget:
    def replication_errors_search_expression(metric_name: str):
        return " ".join(
            [
                "{AWS/S3,DestinationBucket,RuleId,SourceBucket}",
                f'DestinationBucket="{bucket.bucket_name}"',
                f'MetricName="{metric_name}"',
            ]
        )

    def replication_expression(metric_name: str, search_region: str, color: OpsDashboardWidgetColor | None = None):
        return cloudwatch.MathExpression(
            expression=metric_search_expression_fn(
                expression=replication_errors_search_expression(metric_name),
                aggregator="Sum",
                time=replication_time_mins * 60,
            ),
            label="",
            search_region=search_region,
            color=color,
        )

    replication_errors = [
        replication_expression(
            metric_name="OperationsFailedReplication",
            search_region=search_region,
            color=OpsDashboardWidgetColor.Red,
        )
        for search_region in search_regions
    ]

    replication_operations = [
        replication_expression(
            metric_name="OperationsPendingReplication",
            search_region=search_region,
            color=OpsDashboardWidgetColor.Blue,
        )
        for search_region in search_regions
    ]

    return cloudwatch.GraphWidget(
        left=replication_operations,
        right=replication_errors,
        title="Pending ops <- S3 Replication -> Failed ops",
        height=OPS_DASHBOARD_WIDGET_HEIGHT,
        width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
        statistic="Sum",
        period=aws_cdk.Duration.minutes(replication_time_mins),
    )


def _create_s3_buckets_widget(buckets: list[s3.IBucket]) -> cloudwatch.IWidget:
    def s3_metric(bucket_name: str, metric_name: str = "BucketSizeBytes", storage_type: str = "StandardStorage"):
        return cloudwatch.Metric(
            namespace="AWS/S3",
            metric_name=metric_name,
            dimensions_map={
                "BucketName": bucket_name,
                "StorageType": storage_type,
            },
        )

    return cloudwatch.GraphWidget(
        left=[s3_metric(bn.bucket_name) for bn in buckets],
        title="S3 Bucket Size",
        height=OPS_DASHBOARD_WIDGET_HEIGHT,
        width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
        statistic="Average",
        period=aws_cdk.Duration.days(1),
    )


def _create_glue_etl_widgets(job: "glue_alpha.IJob", period_hours: int) -> list[cloudwatch.IWidget]:
    def etl_metric(
        metric_name: str,
        dimensions: dict[str, str] = {},
        color: OpsDashboardWidgetColor | None = None,
        period: aws_cdk.Duration | None = None,
    ):
        return cloudwatch.Metric(
            namespace="Glue",
            metric_name=metric_name,
            dimensions_map={
                "JobRunId": "ALL",
                "JobName": job.job_name,
                **dimensions,
            },
            color=color,
            period=period,
        )

    return [
        cloudwatch.GraphWidget(
            left=[
                etl_metric(
                    "glue.succeed.ALL",
                    {"Type": "count", "ObservabilityGroup": "error"},
                    OpsDashboardWidgetColor.Green,
                )
            ],
            right=[
                etl_metric(
                    "glue.error.ALL",
                    {"Type": "count", "ObservabilityGroup": "error"},
                    OpsDashboardWidgetColor.Red,
                )
            ],
            title="ETL Jobs <- Glue -> ETL errors",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.hours(period_hours),
        ),
        cloudwatch.GraphWidget(
            left=[
                etl_metric("glue.ALL.system.cpuSystemLoad", {"Type": "gauge"}),
                etl_metric(
                    "glue.ALL.memory.total.used.percentage",
                    {"Type": "gauge", "ObservabilityGroup": "resource_utilization"},
                ),
                etl_metric(
                    "glue.ALL.disk.used.percentage",
                    {"Type": "gauge", "ObservabilityGroup": "resource_utilization"},
                ),
            ],
            left_y_axis=cloudwatch.YAxisProps(
                label="Percentage",
                show_units=False,
            ),
            left_annotations=[
                cloudwatch.HorizontalAnnotation(
                    value=0.8,
                    color=OpsDashboardWidgetColor.Red,
                    label="80 %",
                )
            ],
            title="ETL Resource utilization",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Average",
            period=aws_cdk.Duration.hours(period_hours),
        ),
        cloudwatch.GraphWidget(
            left=[etl_metric("glue.ALL.s3.filesystem.write_bytes", {"Type": "gauge"})],
            title="ETL output to S3",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.hours(period_hours),
        ),
    ]


def _create_glue_etl_alarm(scope, job: "glue_alpha.IJob") -> cloudwatch.IAlarm:
    def etl_metric(
        metric_name: str,
        dimensions: dict[str, str] = {},
        color: OpsDashboardWidgetColor | None = None,
        period: aws_cdk.Duration | None = None,
    ):
        return cloudwatch.Metric(
            namespace="Glue",
            metric_name=metric_name,
            dimensions_map={
                "JobRunId": "ALL",
                "JobName": job.job_name,
                **dimensions,
            },
            color=color,
            period=period,
        )

    return cloudwatch.Alarm(
        scope,
        "AlarmETLError",
        metric=etl_metric(
            "glue.error.ALL",
            {"Type": "count", "ObservabilityGroup": "error"},
            period=aws_cdk.Duration.hours(1),
        ),
        treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        threshold=1,
        evaluation_periods=1,
        datapoints_to_alarm=1,
        comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        alarm_name=f"{job.job_name}-error-alarm",
        alarm_description=f"Alarm for ETL errors in {job.job_name}",
    )


def _layout_dashboard_widgets(
    monitoring_widgets: list[cloudwatch.IWidget], monitoring_alarms: list[cloudwatch.IAlarm] | None = None
) -> list[list[cloudwatch.IWidget]]:
    curr_row_len = 0
    curr_row = []
    ret_val = []

    if monitoring_alarms:
        curr_row.append(
            cloudwatch.AlarmStatusWidget(
                alarms=monitoring_alarms,
                title="Alarms",
                height=OPS_DASHBOARD_WIDGET_HEIGHT,
                width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            )
        )
        curr_row_len += OPS_DASHBOARD_WIDGET_WIDTH_QUARTER

    for widget in monitoring_widgets:
        if widget.width + curr_row_len <= OPS_DASHBOARD_TOTAL_WIDTH:
            curr_row.append(widget)
            curr_row_len += widget.width
        else:
            ret_val.append(curr_row)
            curr_row = [widget]
            curr_row_len = widget.width

    if curr_row:
        ret_val.append(curr_row)

    return ret_val


def _discover_classes(module: typing.Any, base_class: type, critical_names: set[str]) -> list[tuple[str, bool]]:
    classes = set()

    def add_matching_classes(mod):
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, base_class) and obj is not base_class and hasattr(obj, "__name__"):
                classes.add(obj.__name__)

    # Check current module
    add_matching_classes(module)

    # Check submodules recursively
    if hasattr(module, "__path__"):
        for _, modname, _ in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
            try:
                add_matching_classes(__import__(modname, fromlist=[""]))
            except (ImportError, AttributeError):
                pass

    return [(cls, cls in critical_names) for cls in sorted(classes)]


def _create_command_widgets(namespace: str, service: str, commands: list[tuple[str, bool]]) -> list[cloudwatch.IWidget]:
    if not commands:
        return []

    def command_metric(command_name: str, metric_type: str, color: OpsDashboardWidgetColor | None = None):
        return cloudwatch.Metric(
            namespace=namespace,
            metric_name=command_name,
            dimensions_map={"service": service, "type": metric_type},
            color=color,
            label=command_name,
        )

    return [
        cloudwatch.GraphWidget(
            left=[command_metric(cmd, "SuccessfullCommand", OpsDashboardWidgetColor.Green) for cmd, _ in commands],
            right=[command_metric(cmd, "FailedCommand", OpsDashboardWidgetColor.Red) for cmd, _ in commands],
            title="Successful <- Commands -> Failed",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        )
    ]


def _create_command_alarms(
    scope,
    namespace: str,
    service: str,
    commands: list[tuple[str, bool]],
    alarm_naming_convention: typing.Callable[[str], str],
) -> list[cloudwatch.IAlarm]:
    alarms = []

    for command_name in (command_name for command_name, create_alarm in commands if create_alarm):

        alarms.append(
            cloudwatch.Alarm(
                scope,
                f"AlarmCommandFailed{command_name.replace(' ', '')}",
                metric=cloudwatch.Metric(
                    namespace=namespace,
                    metric_name=command_name,
                    dimensions_map={"service": service, "type": "FailedCommand"},
                    period=aws_cdk.Duration.minutes(5),
                ),
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                threshold=1,
                evaluation_periods=1,
                datapoints_to_alarm=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_name=alarm_naming_convention(command_name.lower()),
                alarm_description=f"Alarm for failed command {command_name} in {service} bounded context",
            )
        )

    return alarms


def _create_domain_event_widgets(
    namespace: str, service: str, events: list[tuple[str, bool]]
) -> list[cloudwatch.IWidget]:
    if not events:
        return []

    def event_metric(event_name: str):
        return cloudwatch.Metric(
            namespace=namespace,
            metric_name=event_name,
            dimensions_map={"service": service, "type": "DomainEvent"},
            label=event_name,
        )

    return [
        cloudwatch.GraphWidget(
            left=[event_metric(evt) for evt, _ in events],
            title="Domain Events Published",
            height=OPS_DASHBOARD_WIDGET_HEIGHT,
            width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
            statistic="Sum",
            period=aws_cdk.Duration.minutes(5),
        )
    ]


def _create_domain_event_alarms(
    scope,
    namespace: str,
    service: str,
    events: list[tuple[str, bool]],
    alarm_naming_convention: typing.Callable[[str], str],
) -> list[cloudwatch.IAlarm]:
    alarms = []

    for event_name in (event_name for event_name, create_alarm in events if create_alarm):

        alarms.append(
            cloudwatch.Alarm(
                scope,
                f"AlarmDomainEvent{event_name.replace(' ', '')}",
                metric=cloudwatch.Metric(
                    namespace=namespace,
                    metric_name=event_name,
                    dimensions_map={"service": service, "type": "DomainEvent"},
                    period=aws_cdk.Duration.minutes(5),
                ),
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                threshold=1,
                evaluation_periods=1,
                datapoints_to_alarm=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_name=alarm_naming_convention(event_name.lower()),
                alarm_description=f"Alarm for domain event {event_name} in {service} bounded context",
            )
        )

    return alarms


def _create_step_functions_widget(state_machines: list[sfn.StateMachine]) -> cloudwatch.IWidget:
    def sfn_metric(state_machine: sfn.StateMachine, metric_name: str, color: OpsDashboardWidgetColor | None = None):
        return cloudwatch.Metric(
            namespace="AWS/States",
            metric_name=metric_name,
            dimensions_map={"StateMachineArn": state_machine.state_machine_arn},
            color=color,
            label=f"{state_machine.state_machine_name} {metric_name}",
        )

    return cloudwatch.GraphWidget(
        left=[sfn_metric(sm, "ExecutionsStarted", OpsDashboardWidgetColor.Green) for sm in state_machines],
        right=[
            *[sfn_metric(sm, "ExecutionsFailed", OpsDashboardWidgetColor.Red) for sm in state_machines],
            *[sfn_metric(sm, "ExecutionsTimedOut", OpsDashboardWidgetColor.Orange) for sm in state_machines],
        ],
        title="Started <- Step Functions -> Failed/TimedOut",
        height=OPS_DASHBOARD_WIDGET_HEIGHT,
        width=OPS_DASHBOARD_WIDGET_WIDTH_QUARTER,
        statistic="Sum",
        period=aws_cdk.Duration.minutes(5),
    )


def _create_step_functions_alarms(scope, state_machines: list[sfn.StateMachine]) -> list[cloudwatch.IAlarm]:
    def sfn_metric(state_machine: sfn.IStateMachine, metric_name: str):
        return cloudwatch.Metric(
            namespace="AWS/States",
            metric_name=metric_name,
            dimensions_map={"StateMachineArn": state_machine.state_machine_arn},
            period=aws_cdk.Duration.minutes(5),
        )

    alarms = []
    for idx, sm in enumerate(state_machines):
        alarms.extend(
            [
                cloudwatch.Alarm(
                    scope,
                    f"AlarmStepFunctionFailed{sm.node.id}",
                    metric=sfn_metric(sm, "ExecutionsFailed"),
                    treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                    threshold=1,
                    evaluation_periods=1,
                    datapoints_to_alarm=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                    alarm_name=f"{sm.state_machine_name}-failed",
                    alarm_description="Alarm for failed executions in Step Function",
                ),
                cloudwatch.Alarm(
                    scope,
                    f"AlarmStepFunctionTimedOut{sm.node.id}",
                    metric=sfn_metric(sm, "ExecutionsTimedOut"),
                    treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                    threshold=1,
                    evaluation_periods=1,
                    datapoints_to_alarm=1,
                    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                    alarm_name=f"{sm.state_machine_name}-timedout",
                    alarm_description="Alarm for timed out executions in Step Function",
                ),
            ]
        )

    return alarms
