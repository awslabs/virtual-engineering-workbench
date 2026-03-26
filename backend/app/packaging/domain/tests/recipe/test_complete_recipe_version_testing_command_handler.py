import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import complete_recipe_version_testing_command_handler
from app.packaging.domain.model.recipe import recipe_version, recipe_version_test_execution


@pytest.fixture
def get_test_recipe_version_test_execution_with_specific_instance_id_and_test_command_status():
    def _get_test_recipe_version_test_execution_with_specific_instance_id_and_test_command_status(
        instance_id: str,
        test_command_status: str,
        get_test_execution_id,
        mock_recipe_version_object,
        mock_recipe_object,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=get_test_execution_id,
            instanceId=instance_id,
            instanceArchitecture=mock_recipe_object.recipeArchitecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=mock_recipe_object.recipeOsVersion,
            instancePlatform=mock_recipe_object.recipePlatform,
            instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected.value,
            setupCommandError="This is an example error",
            setupCommandId="ef7fdfd8-9b57-4151-a15c-888888888888",
            setupCommandOutput="This is an example output",
            setupCommandStatus="SUCCESS",
            testCommandError="This is an example error",
            testCommandId="ef7fdfd8-9b57-4151-a15c-999999999999",
            testCommandOutput="This is an example output",
            testCommandStatus=test_command_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Success.value,
        )

    return _get_test_recipe_version_test_execution_with_specific_instance_id_and_test_command_status


@pytest.mark.parametrize(
    "instance_id, desired_command_status, desired_recipe_status",
    (
        (
            ["i-01234567890abcdef"],
            [recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success],
            [recipe_version.RecipeVersionStatus.Validated],
        ),
        (
            ["i-01234567890abcdef"],
            [recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Failed],
            [recipe_version.RecipeVersionStatus.Failed],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_complete_recipe_version_testing(
    complete_recipe_version_testing_command_mock,
    recipe_query_service_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id_and_test_command_status,
    generic_repo_mock,
    uow_mock,
    mock_recipe_version_object,
    mock_recipe_object,
    get_test_execution_id,
    instance_id,
    desired_command_status,
    desired_recipe_status,
):
    # ARRANGE
    instance_id = list(instance_id)[0]
    desired_command_status = list(desired_command_status)[0]
    desired_recipe_status = list(desired_recipe_status)[0]
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id_and_test_command_status(
            instance_id=instance_id,
            test_command_status=desired_command_status,
            mock_recipe_version_object=mock_recipe_version_object,
            mock_recipe_object=mock_recipe_object,
            get_test_execution_id=get_test_execution_id,
        )
    )

    # ACT
    complete_recipe_version_testing_command_handler.handle(
        command=complete_recipe_version_testing_command_mock,
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
        recipe_version_testing_srv=recipe_version_testing_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    recipe_version_testing_service_mock.teardown_testing_environment.assert_any_call(instance_id=instance_id)
    generic_repo_mock.update_attributes.assert_called_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=mock_recipe_object.recipeId, recipeVersionId=mock_recipe_version_object.recipeVersionId
        ),
        status=desired_recipe_status,
    )
    uow_mock.commit.assert_called()
