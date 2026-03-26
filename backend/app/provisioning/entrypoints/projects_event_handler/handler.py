from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from aws_xray_sdk.core import patch_all

from app.provisioning.domain.commands.product_provisioning import remove_provisioned_product_command
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.value_objects import (
    product_status_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)
from app.provisioning.entrypoints.projects_event_handler import bootstrapper, config
from app.provisioning.entrypoints.projects_event_handler.integration_events import user_unassigned
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app)


@app.handle(user_unassigned.UserUnAssigned)
def user_unassigned_handler(event: user_unassigned.UserUnAssigned):
    # Get non-terminated provisioned products of the user
    user_provisioned_products: list[provisioned_product.ProvisionedProduct] = (
        dependencies.provisioned_products_domain_qry_srv.get_provisioned_products(
            user_id=user_id_value_object.from_str(event.user_id),
            project_id=project_id_value_object.from_str(event.project_id),
            exclude_status=[product_status_value_object.from_str(product_status.ProductStatus.Terminated.value)],
        )
    )

    # Remove each provisioned product
    for pp in user_provisioned_products:
        command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(pp.provisionedProductId),
            project_id=project_id_value_object.from_str(pp.projectId),
            user_id=user_id_value_object.from_str(pp.userId),
        )
        dependencies.command_bus.handle(command)

    # Clean up user profile & maintenance windows
    cleanup_command = cleanup_user_profile_command.CleanUpUserProfileCommand(
        user_id=user_id_value_object.from_str(event.user_id),
    )
    dependencies.command_bus.handle(cleanup_command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ProjectsEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
