import boto3
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.metrics import Metrics, MetricUnit, single_metric
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.entrypoints.scheduled_metric_producer import config
from app.shared.logging import boto_logger
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

tracer = Tracer()
logger = Logger()
metrics = Metrics()

app_config = config.AppConfig()
session = boto_logger.loggable_session(boto3.session.Session(), logger)
dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())


projects_query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
    table_name=app_config.get_table_name(),
    dynamodb_client=dynamodb.meta.client,
    gsi_inverted_primary_key=app_config.get_inverted_primary_key_gsi_name(),
    gsi_aws_accounts=app_config.get_aws_accounts_gsi_name(),
    gsi_entities=app_config.get_entities_gsi_name(),
)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
@metrics.log_metrics
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "ScheduledMetricProducer"}
)
def handler(event: dict, context: LambdaContext):
    all_projects, paging_key, assignments = projects_query_service.list_projects(10, None)
    while paging_key:
        projects_page, paging_key, assignments = projects_query_service.list_projects(10, paging_key)
        all_projects.extend(projects_page)

    total_user_ids = set()

    for project in all_projects:
        all_project_users = projects_query_service.list_users_by_project(project.projectId)

        total_user_ids |= {a.userId for a in all_project_users}

        project_user_count = len(all_project_users)

        with single_metric(name="TotalAssignedUsers", unit=MetricUnit.Count, value=project_user_count) as metric:
            metric.add_dimension(name="Program", value=project.projectName or "n/a")

    with single_metric(name="TotalVEWUsers", unit=MetricUnit.Count, value=len(total_user_ids)):
        ...
