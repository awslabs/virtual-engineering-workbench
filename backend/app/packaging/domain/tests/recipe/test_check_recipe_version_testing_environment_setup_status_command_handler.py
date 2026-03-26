import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    check_recipe_version_testing_environment_setup_status_command_handler,
)
from app.packaging.domain.model.recipe import recipe_version_test_execution


@pytest.fixture
def get_test_recipe_version_test_execution_with_specific_instance_id_and_setup_command():
    def _get_test_recipe_version_test_execution_with_specific_instance_id_and_setup_command(
        instance_id: str,
        setup_command_id: str,
        setup_command_status: str,
        get_test_execution_id,
        mock_recipe_version_object,
        mock_recipe_object,
        status: recipe_version_test_execution.RecipeVersionTestExecutionStatus,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=mock_recipe_version_object.recipeId,
            testExecutionId=get_test_execution_id,
            instanceId=instance_id,
            instanceArchitecture=mock_recipe_object.recipeArchitecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=mock_recipe_object.recipeOsVersion,
            instancePlatform=mock_recipe_object.recipePlatform,
            instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected.value,
            setupCommandId=setup_command_id,
            setupCommandStatus=setup_command_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=status,
        )

    return _get_test_recipe_version_test_execution_with_specific_instance_id_and_setup_command


@pytest.mark.parametrize(
    "instance_id, command_execution, desired_command_status, desired_recipe_version_test_status",
    (
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "status": recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success,
                },
            },
            recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success,
            recipe_version_test_execution.RecipeVersionTestExecutionStatus.Success,
        ),
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "status": recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Failed,
                },
            },
            recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Failed,
            recipe_version_test_execution.RecipeVersionTestExecutionStatus.Failed,
        ),
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "status": recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
                },
            },
            recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
            recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
        ),
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "status": recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Running,
                },
            },
            recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Running,
            recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_check_recipe_version_testing_environment_setup_status(
    check_recipe_version_testing_environment_setup_status_command_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id_and_setup_command,
    recipe_version_test_execution_query_service_mock,
    recipe_version_testing_service_mock,
    generic_repo_mock,
    uow_mock,
    instance_id,
    command_execution,
    desired_command_status,
    desired_recipe_version_test_status,
    get_test_execution_id,
    mock_recipe_version_object,
    mock_recipe_object,
):
    # ARRANGE
    instance_id = list(instance_id)[0]
    command_id = list(command_execution.keys())[0]
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id_and_setup_command(
            instance_id=instance_id,
            setup_command_id=command_id,
            setup_command_status=command_execution[command_id].get("status"),
            get_test_execution_id=get_test_execution_id,
            mock_recipe_version_object=mock_recipe_version_object,
            mock_recipe_object=mock_recipe_object,
            status=desired_recipe_version_test_status,
        )
    )
    recipe_version_testing_service_mock.get_testing_command_status.return_value = command_execution[command_id].get(
        "status"
    )

    # ACT
    testing_environment_setup_command_status = (
        check_recipe_version_testing_environment_setup_status_command_handler.handle(
            command=check_recipe_version_testing_environment_setup_status_command_mock,
            recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            uow=uow_mock,
        )
    )

    # ASSERT
    assertpy.assert_that(testing_environment_setup_command_status).is_equal_to(desired_command_status)
    recipe_version_testing_service_mock.get_testing_command_status.assert_any_call(
        command_id=command_id,
        instance_id=instance_id,
    )

    update_attributes = {"setupCommandStatus": command_execution[command_id].get("status")}
    update_attributes["status"] = desired_recipe_version_test_status.value
    generic_repo_mock.update_attributes.assert_any_call(
        recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=get_test_execution_id,
        ),
        lastUpdateDate="2023-09-29T00:00:00+00:00",
        **update_attributes,
    )
    uow_mock.commit.assert_called()
