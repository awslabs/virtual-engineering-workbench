from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from aws_xray_sdk.core import patch_all

from app.provisioning.domain.commands.product_provisioning import (
    deprovision_provisioned_product_command,
    fail_provisioned_product_update,
    provision_product_command,
    stop_provisioned_product_after_update_complete_command,
    stop_provisioned_product_for_update_command,
    update_provisioned_product_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    start_provisioned_product_command,
    stop_provisioned_product_command,
)
from app.provisioning.domain.events.product_provisioning import (
    insufficient_capacity_reached,
    product_launch_started,
    provisioned_product_removal_retried,
    provisioned_product_removal_started,
    provisioned_product_stop_for_upgrade_failed,
    provisioned_product_stopped_for_update,
    provisioned_product_stopped_for_upgrade,
    provisioned_product_update_initialized,
    provisioned_product_upgraded,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_start_initiated,
    provisioned_product_stop_initiated,
)
from app.provisioning.domain.events.provisioned_product_sync import (
    provisioned_product_status_out_of_sync,
)
from app.provisioning.domain.orchestration import sync_command_resolver
from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    provisioned_product_id_value_object,
)
from app.provisioning.entrypoints.domain_event_handler import bootstrapper, config
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
dependencies = bootstrapper.bootstrap(app_config, logger, app=app)
sync_cmd_resolver = sync_command_resolver.init()

"""
Provisioning events
"""


@app.handle(product_launch_started.ProductLaunchStarted)
def provisioned_product_launch_started_handler(
    event: product_launch_started.ProductLaunchStarted,
):
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
        user_ip_address=ip_address_value_object.from_str(event.user_ip_address),
    )
    dependencies.command_bus.handle(command)


@app.handle(insufficient_capacity_reached.InsufficientCapacityReached)
def insufficient_capacity_reached_handler(
    event: insufficient_capacity_reached.InsufficientCapacityReached,
):
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
        user_ip_address=ip_address_value_object.from_str(event.user_ip_address),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_update_initialized.ProvisionedProductUpdateInitialized)
def provisioned_product_update_initialized_handler(
    event: provisioned_product_update_initialized.ProvisionedProductUpdateInitialized,
):
    command = stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
        user_ip_address=ip_address_value_object.from_str(event.user_ip_address),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade)
def provisioned_product_stopped_for_upgrade_handler(
    event: provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade,
):
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_stopped_for_update.ProvisionedProductStoppedForUpdate)
def provisioned_product_stopped_for_update_handler(
    event: provisioned_product_stopped_for_update.ProvisionedProductStoppedForUpdate,
):
    command = update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_upgraded.ProvisionedProductUpgraded)
def provisioned_product_stopped_after_update_handler(
    event: provisioned_product_upgraded.ProvisionedProductUpgraded,
):
    command = stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed)
def provisioned_product_stop_for_upgrade_failed_handler(
    event: provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed,
):
    command = fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_removal_started.ProvisionedProductRemovalStarted)
def provisioned_product_removal_started_handler(
    event: provisioned_product_removal_started.ProvisionedProductRemovalStarted,
):
    command = deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_removal_retried.ProvisionedProductRemovalRetried)
def provisioned_product_removal_retried_handler(
    event: provisioned_product_removal_retried.ProvisionedProductRemovalRetried,
):
    command = deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
    )
    dependencies.command_bus.handle(command)


"""
State events
"""


@app.handle(provisioned_product_start_initiated.ProvisionedProductStartInitiated)
def provisioned_product_start_initiated_handler(
    event: provisioned_product_start_initiated.ProvisionedProductStartInitiated,
):
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
        user_ip_address=ip_address_value_object.from_str(event.user_ip_address),
    )
    dependencies.command_bus.handle(command)


@app.handle(provisioned_product_stop_initiated.ProvisionedProductStopInitiated)
def provisioned_product_stop_initiated_handler(
    event: provisioned_product_stop_initiated.ProvisionedProductStopInitiated,
):
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
    )
    dependencies.command_bus.handle(command)


"""
Sync events
"""


@app.handle(provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync)
def provisioned_product_status_out_of_sync_handler(
    event: provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync,
):
    command = sync_cmd_resolver.from_sync_event(event)

    if command:
        logger.info(f"Provisioned product ID: {event.provisioned_product_id}")
        dependencies.command_bus.handle(command)
    else:
        logger.warning(
            f"Handling for {event.new_status} when current state is {event.old_status} is not implemented ({event.provisioned_product_id})."
        )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "DomainEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
