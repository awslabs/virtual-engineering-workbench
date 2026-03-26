from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_xray_sdk.core import patch_all

from app.provisioning.domain.commands.provisioned_product_configuration import (
    complete_provisioned_product_configuration_command,
    fail_provisioned_product_configuration_command,
    start_provisioned_product_configuration_command,
)
from app.provisioning.domain.value_objects import failure_reason_value_object, provisioned_product_id_value_object
from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import bootstrapper, config
from app.provisioning.entrypoints.provisioned_product_configuration_event_handler.model import step_function_model
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import step_function_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()
logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.StepFunctionEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app)


@app.handle(step_function_model.StartProvisionedProductConfigurationRequest)
def handle_start_provisoned_product_configuration(
    event: step_function_model.StartProvisionedProductConfigurationRequest,
):
    command = start_provisioned_product_configuration_command.StartProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
    )
    dependencies.command_bus.handle(command)
    return step_function_model.StartProvisionedProductConfigurationResponse().dict(by_alias=True)


@app.handle(step_function_model.GetProvisionedProductConfigurationStatusRequest)
def handle_get_provisoned_product_configuration_status(
    event: step_function_model.GetProvisionedProductConfigurationStatusRequest,
):
    status, reason = (
        dependencies.provisioned_product_configuration_domain_qs.get_provisioned_product_configuration_run_status(
            provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
        )
    )
    return step_function_model.GetProvisionedProductConfigurationStatusResponse(status=status, reason=reason).dict(
        by_alias=True
    )


@app.handle(step_function_model.FailProvisionedProductConfigurationRequest)
def handle_fail_provisoned_product_configuration(
    event: step_function_model.FailProvisionedProductConfigurationRequest,
):
    command = fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
        reason=failure_reason_value_object.from_str(event.reason),
    )
    dependencies.command_bus.handle(command)
    return step_function_model.FailProvisionedProductConfigurationResponse().dict(by_alias=True)


@app.handle(step_function_model.CompleteProvisionedProductConfigurationRequest)
def handle_complete_provisioned_product_configuration(
    event: step_function_model.CompleteProvisionedProductConfigurationRequest,
):
    command = complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id),
    )
    dependencies.command_bus.handle(command)
    return step_function_model.CompleteProvisionedProductConfigurationResponse().dict(by_alias=True)


@app.handle(step_function_model.IsProvisionedProductReadyRequest)
def handle_is_provisioned_product_ready(
    event: step_function_model.IsProvisionedProductReadyRequest,
):
    is_ready = dependencies.provisioned_product_configuration_domain_qs.is_provisioned_product_ready(
        provisioned_product_id=provisioned_product_id_value_object.from_str(event.provisioned_product_id)
    )
    return step_function_model.IsProvisionedProductReadyResponse(isReady=is_ready).dict(by_alias=True)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "ProvisionedProductConfigurationEventHandler"}
)
@event_source(data_class=step_function_event.StepFunctionEvent)
def handler(
    event: step_function_event.StepFunctionEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
