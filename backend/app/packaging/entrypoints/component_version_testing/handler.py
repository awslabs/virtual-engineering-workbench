from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source

from app.packaging.domain.commands.component import (
    check_component_version_testing_environment_launch_status_command,
    check_component_version_testing_environment_setup_status_command,
    check_component_version_testing_test_status_command,
    complete_component_version_testing_command,
    launch_component_version_testing_environment_command,
    run_component_version_testing_command,
    setup_component_version_testing_environment_command,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import component_version_id_value_object
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)
from app.packaging.entrypoints.component_version_testing import bootstrapper, config
from app.packaging.entrypoints.component_version_testing.model import step_function_model
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import step_function_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
dependencies = bootstrapper.bootstrap(app_config, logger)
app = event_handler.StepFunctionEventResolver(logger=logger)


@app.handle(step_function_model.LaunchTestEnvironmentRequest)
def handle_launch_test_environment_action(event: step_function_model.LaunchTestEnvironmentRequest):
    """Launch the test environment."""

    dependencies.command_bus.handle(
        launch_component_version_testing_environment_command.LaunchComponentVersionTestingEnvironmentCommand(
            componentId=component_id_value_object.from_str(event.component_id),
            componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
            testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.LaunchTestEnvironmentResponse().model_dump(by_alias=True)


@app.handle(step_function_model.CheckTestEnvironmentLaunchStatusRequest)
def handle_check_test_environment_launch_status_action(
    event: step_function_model.CheckTestEnvironmentLaunchStatusResponse,
):
    """Check the test environment launch status."""

    command = check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand(
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    istances_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckTestEnvironmentLaunchStatusResponse(instancesStatus=istances_status).model_dump(
        by_alias=True
    )


@app.handle(step_function_model.SetupTestEnvironmentRequest)
def handle_setup_test_environment_action(
    event: step_function_model.SetupTestEnvironmentRequest,
):
    """Setup the test environment."""

    dependencies.command_bus.handle(
        setup_component_version_testing_environment_command.SetupComponentVersionTestingEnvironmentCommand(
            componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
            testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.SetupTestEnvironmentResponse().model_dump(by_alias=True)


@app.handle(step_function_model.CheckTestEnvironmentSetupStatusRequest)
def handle_check_test_environment_setup_status_action(
    event: step_function_model.CheckTestEnvironmentSetupStatusResponse,
):
    """Check the test environment setup status."""

    command = check_component_version_testing_environment_setup_status_command.CheckComponentVersionTestingEnvironmentSetupStatusCommand(
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    setup_commands_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckTestEnvironmentSetupStatusResponse(
        setupCommandsStatus=setup_commands_status
    ).model_dump(by_alias=True)


@app.handle(step_function_model.RunComponentVersionTestRequest)
def handle_run_component_version_test_action(
    event: step_function_model.RunComponentVersionTestRequest,
):
    """Run the component version test."""

    dependencies.command_bus.handle(
        run_component_version_testing_command.RunComponentVersionTestingCommand(
            componentId=component_id_value_object.from_str(event.component_id),
            componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
            testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.RunComponentVersionTestResponse().model_dump(by_alias=True)


@app.handle(step_function_model.CheckComponentVersionTestStatusRequest)
def handle_check_component_version_test_status_action(
    event: step_function_model.CheckComponentVersionTestStatusResponse,
):
    """Check the component version test status."""

    command = check_component_version_testing_test_status_command.CheckComponentVersionTestingTestStatusCommand(
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    test_commands_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckComponentVersionTestStatusResponse(
        testCommandsStatus=test_commands_status
    ).model_dump(by_alias=True)


@app.handle(step_function_model.CompleteComponentVersionTestRequest)
def handle_complete_component_version_test_action(event: step_function_model.CompleteComponentVersionTestRequest):
    """Complete the component version test and teardown the test environment."""

    command = complete_component_version_testing_command.CompleteComponentVersionTestingCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    component_version_test_status = dependencies.command_bus.handle(command)

    return step_function_model.CompleteComponentVersionTestResponse(
        componentVersionTestStatus=component_version_test_status
    ).model_dump(by_alias=True)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "ComponentVersionTesting"}
)
@event_source(data_class=step_function_event.StepFunctionEvent)
def handler(
    event: step_function_event.StepFunctionEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
