from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.provisioning.domain.model import product_status
from app.provisioning.domain.orchestration import container_command_resolver, instance_command_resolver
from app.provisioning.domain.value_objects import provisioned_product_id_value_object
from app.provisioning.entrypoints.provisioned_product_state_event_handler import bootstrapper, config
from app.provisioning.entrypoints.provisioned_product_state_event_handler.integration_events import (
    container_state_change_notification,
    ec2_state_change_notification,
)
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app=app)
instance_command_resolver = instance_command_resolver.init()
container_command_resolver = container_command_resolver.init()


PROVISIONED_PRODUCT_ARN_TAG_NAME = "aws:servicecatalog:provisionedProductArn"
PROVISIONED_PRODUCT_ID_TAG_NAME = "vew:provisionedProduct:id"


@app.handle(ec2_state_change_notification.EC2StateChangeNotification, event_name="WorkbenchEC2StateChanged")
def handle_ec2_state_change_notification(event: ec2_state_change_notification.EC2StateChangeNotification):
    user_id = app_config.get_bounded_context_name()

    provisioned_product_tags = dependencies.instance_mgmt_srv.get_instance_details(
        instance_id=event.instanceId, region=event.region, aws_account_id=event.accountId, user_id=user_id
    ).tags

    provisioned_product_arn = None

    for t in provisioned_product_tags:
        if t.key == PROVISIONED_PRODUCT_ARN_TAG_NAME:
            provisioned_product_arn = t.value

    if provisioned_product_arn is None:
        logger.warning(
            {
                "Message": "No provisioned product ARN could be found in the instance tags",
            }
        )
        return

    provisioned_product = dependencies.provisioned_products_query_service.get_by_sc_provisioned_product_id(
        sc_provisioned_product_id=provisioned_product_id_value_object.from_service_catalog_arn(
            provisioned_product_arn
        ).value
    )

    if not provisioned_product:
        logger.warning(
            {
                "SCProvisionedProductId": provisioned_product_arn,
                "Message": "Provisioned Product not found in the DB. Ignoring the notification",
            }
        )

        return

    if command := instance_command_resolver.from_ec2_state(
        provisioned_product=provisioned_product, ec2_state=event.state
    ):
        dependencies.command_bus.handle(command)
    else:
        # no commands to be executed when EC2 is changing to starting/stopping/terminating
        return


@app.handle(
    container_state_change_notification.ContainerChangeNotification, event_name="WorkbenchContainerStateChanged"
)
def handle_container_state_change_notification(event: container_state_change_notification.ContainerChangeNotification):
    user_id = app_config.get_bounded_context_name()
    cluster_name = event.clusterArn.split("/")[-1]
    provisioned_product_tags = dependencies.container_mgmt_srv.get_container_tags_from_task_arn(
        aws_account_id=event.accountId,
        region=event.region,
        cluster_name=cluster_name,
        task_arn=event.taskArn,
        user_id=user_id,
    )
    provisioned_product_id = None

    for t in provisioned_product_tags:
        if t.key == PROVISIONED_PRODUCT_ID_TAG_NAME:
            provisioned_product_id = t.value

    if provisioned_product_id is None:
        logger.warning(
            {
                "Message": "No provisioned product ID could be found in the task tags",
            }
        )
        return

    provisioned_product = dependencies.provisioned_products_query_service.get_by_id(
        provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id).value
    )

    if not provisioned_product:
        logger.warning(
            {
                "SCProvisionedProductId": provisioned_product_id,
                "Message": "Provisioned Product not found in the DB. Ignoring the notification",
            }
        )

        return

    if command := container_command_resolver.from_container_state(
        provisioned_product=provisioned_product, container_state=product_status.TaskState(value=event.lastStatus)
    ):
        dependencies.command_bus.handle(command)
    else:
        # no commands to be executed when EC2 is changing to starting/stopping/terminating
        return


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context(log_event=True)  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "VirtualTargetEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
