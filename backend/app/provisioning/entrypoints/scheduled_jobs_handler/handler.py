from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.metrics import MetricUnit, single_metric
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_xray_sdk.core import patch_all

from app.provisioning.domain.commands.product_provisioning import (
    cleanup_provisioned_products_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_batch_stop_command,
    sync_provisioned_product_state_command,
)
from app.provisioning.domain.model import product_status
from app.provisioning.domain.value_objects import (
    product_status_value_object,
    project_id_value_object,
    provisioned_product_cleanup_value_object,
)
from app.provisioning.entrypoints.scheduled_jobs_handler import bootstrapper, config
from app.provisioning.entrypoints.scheduled_jobs_handler.scheduled_job_events import (
    metric_producer_job,
    provisioned_product_batch_stop_job,
    provisioned_product_cleanup_job,
    provisioned_product_sync_job,
)
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import scheduled_job_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

app = event_handler.ScheduledJobEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app)


@app.handle(provisioned_product_sync_job.ProvisionedProductSyncJob)
def provisioned_product_sync_handler(
    event: provisioned_product_sync_job.ProvisionedProductSyncJob,
):
    dependencies.command_bus.handle(sync_provisioned_product_state_command.SyncProvisionedProductStateCommand())


@app.handle(metric_producer_job.MetricProducerJob)
def scheduled_metric_producer_handler(event: metric_producer_job.MetricProducerJob):
    # Get all projects
    projects = dependencies.projects_domain_query_service.get_projects()

    # Loop through projects and get all provisioned products
    total_provisioned_products_count = 0
    distinct_users = set()
    total_running_provisioned_products = 0
    distinct_current_active_users = set()
    for project in projects:
        project_provisioned_products = dependencies.provisioned_products_domain_qry_srv.get_provisioned_products(
            project_id=project_id_value_object.from_str(project.projectId),
            exclude_status=[product_status_value_object.from_str(product_status.ProductStatus.Terminated)],
        )
        distinct_project_users = {pp.userId.upper() for pp in project_provisioned_products}
        distinct_users.update(distinct_project_users)
        total_provisioned_products_count += len(project_provisioned_products)
        project_running_provisioned_products = [
            pp for pp in project_provisioned_products if pp.status == product_status.ProductStatus.Running
        ]
        total_running_provisioned_products += len(project_running_provisioned_products)
        distinct_project_current_active_users = {pp.userId.upper() for pp in project_running_provisioned_products}
        distinct_current_active_users.update(distinct_project_current_active_users)
        distinct_product_names = {pp.productName for pp in project_provisioned_products}

        with single_metric(
            name="TotalProgramProvisionedProducts",
            unit=MetricUnit.Count,
            value=len(project_provisioned_products),
        ) as metric:
            metric.add_dimension(name="Program", value=project.projectName or "n/a")

        with single_metric(
            name="TotalProgramUsersWithProvisionedProducts",
            unit=MetricUnit.Count,
            value=len(distinct_project_users),
        ) as metric:
            metric.add_dimension(name="Program", value=project.projectName or "n/a")

        with single_metric(
            name="TotalProgramRunningProvisionedProducts",
            unit=MetricUnit.Count,
            value=len(project_running_provisioned_products),
        ) as metric:
            metric.add_dimension(name="Program", value=project.projectName or "n/a")

        with single_metric(
            name="TotalProgramCurrentActiveUsers",
            unit=MetricUnit.Count,
            value=len(distinct_project_current_active_users),
        ) as metric:
            metric.add_dimension(name="Program", value=project.projectName or "n/a")

        for product_name in distinct_product_names:
            product_count = sum(1 for pp in project_provisioned_products if pp.productName == product_name)
            with single_metric(
                name="TotalProgramProvisionedProductNames",
                unit=MetricUnit.Count,
                value=product_count,
            ) as metric:
                metric.add_dimension(name="Program", value=project.projectName or "n/a")
                metric.add_dimension(name="ProductName", value=product_name or "n/a")

            running_product_count = sum(
                1 for pp in project_running_provisioned_products if pp.productName == product_name
            )
            with single_metric(
                name="TotalProgramRunningProvisionedProductNames",
                unit=MetricUnit.Count,
                value=running_product_count,
            ) as metric:
                metric.add_dimension(name="Program", value=project.projectName or "n/a")
                metric.add_dimension(name="ProductName", value=product_name or "n/a")

    with single_metric(
        name="TotalProvisionedProducts",
        unit=MetricUnit.Count,
        value=total_provisioned_products_count,
    ):
        ...
    with single_metric(
        name="TotalUsersWithProvisionedProducts",
        unit=MetricUnit.Count,
        value=len(distinct_users),
    ):
        ...
    with single_metric(
        name="TotalRunningProvisionedProducts",
        unit=MetricUnit.Count,
        value=total_running_provisioned_products,
    ):
        ...
    with single_metric(
        name="TotalCurrentActiveUsers",
        unit=MetricUnit.Count,
        value=len(distinct_current_active_users),
    ):
        ...


@app.handle(provisioned_product_cleanup_job.ProvisionedProductCleanupJob)
def scheduled_provisioned_product_cleanup_handler(
    event: provisioned_product_cleanup_job.ProvisionedProductCleanupJob,
):
    command = cleanup_provisioned_products_command.CleanupProvisionedProductsCommand(
        provisioned_product_cleanup_config=provisioned_product_cleanup_value_object.from_json_str(
            dependencies.provisioned_product_cleanup_config
        )
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_batch_stop_job.ProvisionedProductBatchStopJob)
def provisioned_product_batch_stop_handler(
    event: provisioned_product_batch_stop_job.ProvisionedProductBatchStopJob,
):
    dependencies.command_bus.handle(
        initiate_provisioned_product_batch_stop_command.InitiateProvisionedProductBatchStopCommand()
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@event_source(data_class=scheduled_job_event.ScheduledJobEvent)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ScheduledJobs"})
def handler(
    event: scheduled_job_event.ScheduledJobEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
