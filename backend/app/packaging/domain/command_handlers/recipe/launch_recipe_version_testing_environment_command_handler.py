from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import (
    launch_recipe_version_testing_environment_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import (
    recipe_version,
    recipe_version_test_execution,
)
from app.packaging.domain.ports import (
    recipe_query_service,
    recipe_version_query_service,
    recipe_version_testing_service,
)
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_instance_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_entity = recipe_qry_srv.get_recipe(project_id=command.projectId.value, recipe_id=command.recipeId.value)
    if recipe_entity is None:
        raise domain_exception.DomainException(f"Recipe {command.recipeId.value} does not exist.")

    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        command.recipeId.value, command.recipeVersionId.value
    )
    if recipe_version_entity is None:
        raise domain_exception.DomainException(f"Recipe version {command.recipeVersionId.value} does not exist.")
    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_attributes(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            status=recipe_version.RecipeVersionStatus.Testing,
        )
        uow.commit()

    current_time = datetime.now(timezone.utc).isoformat()

    instance_id = recipe_version_test_execution_instance_id_value_object.from_str(
        recipe_version_testing_srv.launch_testing_environment(
            image_upstream_id=recipe_version_entity.parentImageUpstreamId,
            instance_type=recipe_version_testing_srv.get_testing_environment_instance_type(
                architecture=recipe_entity.recipeArchitecture,
                platform=recipe_entity.recipePlatform,
                os_version=recipe_entity.recipeOsVersion,
            ),
            volume_size=int(recipe_version_entity.recipeVersionVolumeSize),
        )
    ).value

    component_version_test_execution_entity = recipe_version_test_execution.RecipeVersionTestExecution(
        recipeVersionId=command.recipeVersionId.value,
        testExecutionId=command.testExecutionId.value,
        instanceId=instance_id,
        instanceArchitecture=recipe_entity.recipeArchitecture,
        instanceImageUpstreamId=recipe_version_entity.parentImageUpstreamId,
        instanceOsVersion=recipe_entity.recipeOsVersion,
        instancePlatform=recipe_entity.recipePlatform,
        # When we launch the instance it starts in DISCONNECTED status
        instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected.value,
        createDate=current_time,
        lastUpdateDate=current_time,
        status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Pending.value,
    )

    with uow:
        uow.get_repository(
            repo_key=recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            repo_type=recipe_version_test_execution.RecipeVersionTestExecution,
        ).add(component_version_test_execution_entity)
        uow.commit()
