from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.provisioning.domain.commands.product_provisioning import (
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
)
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.value_objects import provisioned_product_id_value_object
from app.provisioning.entrypoints.provisioned_product_event_handlers import bootstrapper, config
from app.provisioning.entrypoints.provisioned_product_event_handlers.integration_events import catalog_sns_notification
from app.provisioning.entrypoints.provisioned_product_event_handlers.model import product_cf_stack_status
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app=app)

CF_STACK_RESOURCE_NAME = "AWS::CloudFormation::Stack"


@app.handle(catalog_sns_notification.CatalogSNSNotification, event_name="Catalog SNS notifications")
def handle_catalog_sns_notification(event: catalog_sns_notification.CatalogSNSNotification):
    if event.message.resource_type != CF_STACK_RESOURCE_NAME:
        logger.warning(
            {
                "ResourceType": event.message.resource_type,
                "ExpectedResourceType": CF_STACK_RESOURCE_NAME,
                "Message": "Ignoring notification.",
            }
        )

        return

    provisioned_product = dependencies.provisioned_products_query_service.get_by_sc_provisioned_product_id(
        sc_provisioned_product_id=event.message.sc_provisioned_product_id
    )

    if not provisioned_product:
        logger.warning(
            {
                "SCProvisionedProductId": event.message.sc_provisioned_product_id,
                "Message": "Provisioned Product not found in the DB. Ignoring the notification",
            }
        )

        return

    command = _get_command(event=event, provisioned_product=provisioned_product)

    if command:
        dependencies.command_bus.handle(command)
    else:
        logger.warning(
            {
                "ResourceStatus": event.message.resource_status,
                "ExpectedStatus": product_cf_stack_status.TERMINAL_CREATE_COMPLETE_STATUSES,
                "Message": "Ignoring notification.",
            }
        )


def _get_command(  # noqa: C901
    event: catalog_sns_notification.CatalogSNSNotification, provisioned_product: provisioned_product.ProvisionedProduct
):

    if event.message.resource_status == product_cf_stack_status.ProductCFStackStatus.CREATE_COMPLETE:
        return complete_product_launch_command.CompleteProductLaunchCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    if event.message.resource_status in [
        product_cf_stack_status.ProductCFStackStatus.CREATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.ROLLBACK_COMPLETE,
    ]:
        return fail_product_launch_command.FailProductLaunchCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    if event.message.resource_status == product_cf_stack_status.ProductCFStackStatus.DELETE_COMPLETE:
        return complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    if event.message.resource_status == product_cf_stack_status.ProductCFStackStatus.DELETE_FAILED:
        return fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    if event.message.resource_status == product_cf_stack_status.ProductCFStackStatus.UPDATE_COMPLETE:
        return complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    if event.message.resource_status in [
        product_cf_stack_status.ProductCFStackStatus.UPDATE_FAILED,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_COMPLETE,
        product_cf_stack_status.ProductCFStackStatus.UPDATE_ROLLBACK_FAILED,
    ]:
        return fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(
                provisioned_product.provisionedProductId
            )
        )

    return None


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context(log_event=True)  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ProvisioningEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
