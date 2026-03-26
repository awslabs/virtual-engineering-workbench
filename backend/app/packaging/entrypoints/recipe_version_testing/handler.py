from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source

from app.packaging.domain.commands.recipe import (
    check_recipe_version_testing_environment_launch_status_command,
    check_recipe_version_testing_environment_setup_status_command,
    check_recipe_version_testing_test_status_command,
    complete_recipe_version_testing_command,
    launch_recipe_version_testing_environment_command,
    run_recipe_version_testing_command,
    setup_recipe_version_testing_environment_command,
)
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.packaging.entrypoints.recipe_version_testing import bootstrapper, config
from app.packaging.entrypoints.recipe_version_testing.model import step_function_model
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
        launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand(
            projectId=project_id_value_object.from_str(event.project_id),
            recipeId=recipe_id_value_object.from_str(event.recipe_id),
            recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
            testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.LaunchTestEnvironmentResponse().dict(by_alias=True)


@app.handle(step_function_model.CheckTestEnvironmentLaunchStatusRequest)
def handle_check_test_environment_launch_status_action(
    event: step_function_model.CheckTestEnvironmentLaunchStatusResponse,
):
    """Check the test environment launch status."""

    command = check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    instance_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckTestEnvironmentLaunchStatusResponse(instanceStatus=instance_status).dict(
        by_alias=True
    )


@app.handle(step_function_model.SetupTestEnvironmentRequest)
def handle_setup_test_environment_action(
    event: step_function_model.SetupTestEnvironmentRequest,
):
    """Setup the test environment."""

    dependencies.command_bus.handle(
        setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand(
            recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
            testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.SetupTestEnvironmentResponse().dict(by_alias=True)


@app.handle(step_function_model.CheckTestEnvironmentSetupStatusRequest)
def handle_check_test_environment_setup_status_action(
    event: step_function_model.CheckTestEnvironmentSetupStatusResponse,
):
    """Check the test environment setup status."""

    command = check_recipe_version_testing_environment_setup_status_command.CheckRecipeVersionTestingEnvironmentSetupStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    setup_command_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckTestEnvironmentSetupStatusResponse(setupCommandStatus=setup_command_status).dict(
        by_alias=True
    )


@app.handle(step_function_model.RunRecipeVersionTestRequest)
def handle_run_recipe_version_test_action(
    event: step_function_model.RunRecipeVersionTestRequest,
):
    """Run the recipe version test."""

    dependencies.command_bus.handle(
        run_recipe_version_testing_command.RunRecipeVersionTestingCommand(
            recipeId=recipe_id_value_object.from_str(event.recipe_id),
            recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
            testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
        )
    )

    return step_function_model.RunRecipeVersionTestResponse().dict(by_alias=True)


@app.handle(step_function_model.CheckRecipeVersionTestStatusRequest)
def handle_check_recipe_version_test_status_action(
    event: step_function_model.CheckRecipeVersionTestStatusResponse,
):
    """Check the recipe version test status."""

    command = check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand(
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    test_command_status = dependencies.command_bus.handle(command)

    return step_function_model.CheckRecipeVersionTestStatusResponse(testCommandStatus=test_command_status).dict(
        by_alias=True
    )


@app.handle(step_function_model.CompleteRecipeVersionTestRequest)
def handle_complete_recipe_version_test_action(event: step_function_model.CompleteRecipeVersionTestRequest):
    """Complete the recipe version test and teardown the test environment."""

    command = complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        testExecutionId=recipe_version_test_execution_id_value_object.from_str(event.test_execution_id),
    )

    recipe_version_test_status = dependencies.command_bus.handle(command)

    return step_function_model.CompleteRecipeVersionTestResponse(
        recipeVersionTestStatus=recipe_version_test_status
    ).dict(by_alias=True)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "RecipeVersionTesting"})
@event_source(data_class=step_function_event.StepFunctionEvent)
def handler(
    event: step_function_event.StepFunctionEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
