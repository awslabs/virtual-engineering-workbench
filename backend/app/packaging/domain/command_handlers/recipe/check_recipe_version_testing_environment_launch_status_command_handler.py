from datetime import datetime, timedelta, timezone

from app.packaging.domain.commands.recipe import check_recipe_version_testing_environment_launch_status_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.ports import recipe_version_test_execution_query_service, recipe_version_testing_service
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_instance_status_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __update_attributes(
    command: check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand,
    uow: unit_of_work.UnitOfWork,
    instanceStatus: recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus,
    status: recipe_version_test_execution.RecipeVersionTestExecutionStatus,
):
    with uow:
        uow.get_repository(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            recipe_version_test_execution.RecipeVersionTestExecution,
        ).update_attributes(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
                recipeVersionId=command.recipeVersionId.value, testExecutionId=command.testExecutionId.value
            ),
            instanceStatus=instanceStatus,
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            status=status,
        )
        uow.commit()


def handle(
    command: check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand,
    recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_test_execution_entity = recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
        version_id=command.recipeVersionId.value, test_execution_id=command.testExecutionId.value
    )

    environment_status = recipe_version_test_execution_instance_status_value_object.from_str(
        recipe_version_testing_srv.get_testing_environment_status(
            instance_id=recipe_version_test_execution_entity.instanceId
        )
    ).value
    match environment_status:
        case recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected:
            current_timestamp = datetime.now()
            # If an instance is not CONNECTED after 5 minutes we time out
            if abs(
                current_timestamp
                - datetime.strptime(
                    recipe_version_testing_srv.get_testing_environment_creation_time(
                        instance_id=recipe_version_test_execution_entity.instanceId
                    ),
                    "%Y-%m-%d %H:%M:%S",
                )
            ) > timedelta(minutes=5):
                __update_attributes(
                    command=command,
                    uow=uow,
                    instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected,
                    status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Failed,
                )
                raise domain_exception.DomainException("Testing environment launch has timed out.")
        case recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected:
            __update_attributes(
                command=command,
                uow=uow,
                instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected,
                status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
            )

    return environment_status
