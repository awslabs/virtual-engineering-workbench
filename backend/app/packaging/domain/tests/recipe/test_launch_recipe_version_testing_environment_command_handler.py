import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    launch_recipe_version_testing_environment_command_handler,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import (
    recipe_version,
    recipe_version_test_execution,
)


@freeze_time("2023-09-29")
def test_handle_should_launch_recipe_version_testing(
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    recipe_version_testing_service_mock,
    launch_recipe_version_testing_environment_command_mock,
    generic_repo_mock,
    uow_mock,
    mock_recipe_object,
    mock_recipe_version_object,
    get_test_instance_id,
    get_test_instance_type,
    get_test_recipe_version_id,
    get_test_execution_id,
):
    # ARRANGE
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version_object
    recipe_version_testing_service_mock.get_testing_environment_instance_type.return_value = get_test_instance_type
    recipe_version_testing_service_mock.launch_testing_environment.return_value = get_test_instance_id

    # ACT
    launch_recipe_version_testing_environment_command_handler.handle(
        command=launch_recipe_version_testing_environment_command_mock,
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_version_testing_srv=recipe_version_testing_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=launch_recipe_version_testing_environment_command_mock.recipeId.value,
            recipeVersionId=launch_recipe_version_testing_environment_command_mock.recipeVersionId.value,
        ),
        status=recipe_version.RecipeVersionStatus.Testing,
    )
    recipe_version_testing_service_mock.get_testing_environment_instance_type.assert_any_call(
        architecture=mock_recipe_object.recipeArchitecture,
        platform=mock_recipe_object.recipePlatform,
        os_version=mock_recipe_object.recipeOsVersion,
    )
    recipe_version_testing_service_mock.launch_testing_environment.assert_any_call(
        image_upstream_id=mock_recipe_version_object.parentImageUpstreamId,
        instance_type=get_test_instance_type,
        volume_size=int(mock_recipe_version_object.recipeVersionVolumeSize),
    )
    generic_repo_mock.add.assert_any_call(
        recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=get_test_recipe_version_id,
            testExecutionId=get_test_execution_id,
            instanceId=get_test_instance_id,
            instanceArchitecture=mock_recipe_object.recipeArchitecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=mock_recipe_object.recipeOsVersion,
            instancePlatform=mock_recipe_object.recipePlatform,
            instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected.value,
            createDate="2023-09-29T00:00:00+00:00",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Pending.value,
        )
    )
    uow_mock.commit.assert_called()


def test_handle_should_raise_exception_when_recipe_is_none(
    launch_recipe_version_testing_environment_command_mock,
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    recipe_version_testing_service_mock,
    uow_mock,
):
    # ARRANGE
    recipe_query_service_mock.get_recipe.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch_recipe_version_testing_environment_command_handler.handle(
            command=launch_recipe_version_testing_environment_command_mock,
            recipe_qry_srv=recipe_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe {launch_recipe_version_testing_environment_command_mock.recipeId.value} does not exist."
    )


def test_handle_should_raise_exception_when_recipe_version_is_none(
    launch_recipe_version_testing_environment_command_mock,
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    recipe_version_testing_service_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch_recipe_version_testing_environment_command_handler.handle(
            command=launch_recipe_version_testing_environment_command_mock,
            recipe_qry_srv=recipe_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe version {launch_recipe_version_testing_environment_command_mock.recipeVersionId.value} does not exist."
    )
