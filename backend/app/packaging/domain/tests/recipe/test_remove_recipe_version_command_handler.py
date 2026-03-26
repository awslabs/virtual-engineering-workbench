from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import remove_recipe_version_command_handler
from app.packaging.domain.events.recipe import recipe_version_retirement_failed
from app.packaging.domain.model.recipe import recipe_version


@freeze_time("2023-10-12")
def test_handle_should_raise_exception_when_recipe_version_can_t_be_deleted(
    component_version_service_mock,
    generic_repo_mock,
    recipe_version_service_mock,
    remove_recipe_version_command_mock,
    message_bus_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_service_mock.delete.side_effect = Exception()

    # ACT
    remove_recipe_version_command_handler.handle(
        command=remove_recipe_version_command_mock,
        message_bus=message_bus_mock,
        uow=uow_mock,
        component_version_service=component_version_service_mock,
        recipe_version_service=recipe_version_service_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=remove_recipe_version_command_mock.recipeId.value,
            recipeVersionId=remove_recipe_version_command_mock.recipeVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=recipe_version.RecipeVersionStatus.Failed,
    )
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_retirement_failed.RecipeVersionRetirementFailed(
            projectId=remove_recipe_version_command_mock.projectId.value,
            recipeName=remove_recipe_version_command_mock.recipeName.value,
            recipeVersionName=remove_recipe_version_command_mock.recipeVersionName.value,
            lastUpdatedBy=remove_recipe_version_command_mock.lastUpdatedBy.value,
        )
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_remove_recipe_version(
    component_version_service_mock,
    generic_repo_mock,
    recipe_version_service_mock,
    remove_recipe_version_command_mock,
    message_bus_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_service_mock.delete.return_value = None

    # ACT
    remove_recipe_version_command_handler.handle(
        command=remove_recipe_version_command_mock,
        message_bus=message_bus_mock,
        uow=uow_mock,
        component_version_service=component_version_service_mock,
        recipe_version_service=recipe_version_service_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=remove_recipe_version_command_mock.recipeId.value,
            recipeVersionId=remove_recipe_version_command_mock.recipeVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=recipe_version.RecipeVersionStatus.Retired,
    )
    uow_mock.commit.assert_called()
