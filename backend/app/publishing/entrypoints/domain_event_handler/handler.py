from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from aws_xray_sdk.core import patch_all

from app.publishing.domain.commands import (
    publish_version_command,
    rename_version_distributions_command,
    unpublish_product_command,
    unpublish_version_command,
    update_product_availability_command,
)
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    project_id_value_object,
    version_id_value_object,
)
from app.publishing.entrypoints.domain_event_handler import bootstrapper, config
from app.publishing.entrypoints.domain_event_handler.integration_events import (
    product_archiving_started,
    product_unpublished,
    product_version_ami_shared,
    product_version_name_updated,
    product_version_published,
    product_version_retirement_started,
    product_version_unpublished,
)
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)
app = event_handler.EventBridgeEventResolver(logger=logger)

logger.debug("Dummy change to trigger env variable deployment.")


@app.handle(product_version_ami_shared.ProductVersionAmiShared)
def product_version_ami_shared_handler(
    event: product_version_ami_shared.ProductVersionAmiShared,
):
    command = publish_version_command.PublishVersionCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
        previousEventName=event_name_value_object.from_str(event.previous_event_name),
        oldVersionId=event.old_version_id,
    )

    dependencies.command_bus.handle(command)


@app.handle(product_version_name_updated.ProductVersionNameUpdated)
def product_version_name_updated_handler(
    event: product_version_name_updated.ProductVersionNameUpdated,
):
    command = rename_version_distributions_command.RenameVersionDistributionsCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(product_archiving_started.ProductArchivingStarted)
def product_archiving_started_handler(
    event: product_archiving_started.ProductArchivingStarted,
):
    command = unpublish_product_command.UnpublishProductCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        productId=product_id_value_object.from_str(event.product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(product_version_retirement_started.ProductVersionRetirementStarted)
def product_version_retirement_started_handler(
    event: product_version_retirement_started.ProductVersionRetirementStarted,
):
    command = unpublish_version_command.UnpublishVersionCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(product_version_published.ProductVersionPublished)
def product_version_published_handler(
    event: product_version_published.ProductVersionPublished,
):
    command = update_product_availability_command.UpdateProductAvailabilityCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        productId=product_id_value_object.from_str(event.product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(product_version_unpublished.ProductVersionUnpublished)
def product_version_unpublished_handler(
    event: product_version_unpublished.ProductVersionUnpublished,
):
    command = update_product_availability_command.UpdateProductAvailabilityCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        productId=product_id_value_object.from_str(event.product_id),
    )
    dependencies.command_bus.handle(command)


@app.handle(product_unpublished.ProductUnpublished)
def product_unpublished_handler(event: product_unpublished.ProductUnpublished):
    command = update_product_availability_command.UpdateProductAvailabilityCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        productId=product_id_value_object.from_str(event.product_id),
    )
    dependencies.command_bus.handle(command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "DomainEvents"},
    enable_audit=True,
    region_name=default_region_name,
    secret_name=secret_name,
)
@event_source(data_class=EventBridgeEvent)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
