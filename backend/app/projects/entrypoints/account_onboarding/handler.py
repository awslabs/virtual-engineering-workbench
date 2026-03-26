import json
import os

from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source

from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
    fail_project_account_onboarding_command,
    setup_dynamic_resources_command,
    setup_prerequisites_resources_command,
    setup_static_resources_command,
)
from app.projects.domain.value_objects import (
    account_error_message_value_object,
    account_id_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
    variables_value_object,
)
from app.projects.entrypoints.account_onboarding import bootstrapper, config
from app.projects.entrypoints.account_onboarding.model import step_function_model
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import step_function_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.StepFunctionEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app)


@app.handle(step_function_model.SetupDynamicResourcesRequest)
def handle_setup_dynamic_resources(event: step_function_model.SetupDynamicResourcesRequest):
    cmd = setup_dynamic_resources_command.SetupDynamicResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str(event.account_id),
        region=region_value_object.from_str(event.region),
    )

    dependencies.command_bus.handle(cmd)
    return step_function_model.SetupDynamicResourcesResponse().dict(by_alias=True)


@app.handle(step_function_model.SetupPrerequisitesResourcesRequest)
def handle_setup_prerequisites_resources(event: step_function_model.SetupPrerequisitesResourcesRequest):
    cmd = setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str(event.account_id),
        region=region_value_object.from_str(event.region),
        variables=variables_value_object.from_dict(event.variables) if event.variables else None,
    )

    dependencies.command_bus.handle(cmd)

    return step_function_model.SetupPrerequisitesResourcesResponse().dict(by_alias=True)


@app.handle(step_function_model.SetupStaticResourcesRequest)
def handle_setup_static_resources(event: step_function_model.SetupStaticResourcesRequest):
    cmd = setup_static_resources_command.SetupStaticResourcesCommand(
        aws_account_id=aws_account_id_value_object.from_str(event.account_id),
        region=region_value_object.from_str(event.region),
        variables=variables_value_object.from_dict(event.variables) if event.variables else None,
    )

    dependencies.command_bus.handle(cmd)

    return step_function_model.SetupStaticResourcesResponse().dict(by_alias=True)


@app.handle(step_function_model.CompleteProjectAccountOnboardingRequest)
def handle_complete_project_account_onboarding(event: step_function_model.CompleteProjectAccountOnboardingRequest):
    cmd = complete_project_account_onboarding_command.CompleteProjectAccountOnboarding(
        project_id=project_id_value_object.from_str(event.project_id),
        account_id=account_id_value_object.from_str(event.project_account_id),
    )

    dependencies.command_bus.handle(cmd)

    return step_function_model.CompleteProjectAccountOnboardingResponse().dict(by_alias=True)


@app.handle(step_function_model.FailProjectAccountOnboardingRequest)
def handle_fail_project_account_onboarding(event: step_function_model.FailProjectAccountOnboardingRequest):
    cmd = fail_project_account_onboarding_command.FailProjectAccountOnboarding(
        project_id=project_id_value_object.from_str(event.project_id),
        account_id=account_id_value_object.from_str(event.project_account_id),
        error=account_error_message_value_object.from_str(error=event.error, cause=event.cause),
    )

    dependencies.command_bus.handle(cmd)

    return step_function_model.FailProjectAccountOnboardingResponse().dict(by_alias=True)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "AccountOnboarding"})
@event_source(data_class=step_function_event.StepFunctionEvent)
def handler(
    event: step_function_event.StepFunctionEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)


def main():
    try:
        return handler(
            event=json.loads(os.environ["EVENT"]),
            context=dependencies.task_context_qry_srv.get_task_context(),
        )
    except Exception as e:
        if task_token := os.environ.get("TASK_TOKEN", None):
            dependencies.step_functions_service.send_callback_failure(
                callback_token=task_token, error_type=type(e).__name__, error_message=str(e)
            )
        raise


# The entrypoint for executing Fargate task
if __name__ == "__main__":
    main()
