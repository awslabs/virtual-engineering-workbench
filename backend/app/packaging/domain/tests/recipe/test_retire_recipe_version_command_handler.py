import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import retire_recipe_version_command_handler
from app.packaging.domain.events.recipe import recipe_version_retirement_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def test_handle_should_raise_exception_when_recipe_version_is_not_found(
    get_retire_recipe_version_command_mock,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    retire_recipe_version_command_mock = get_retire_recipe_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_recipe_version_command_handler.handle(
            command=retire_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {retire_recipe_version_command_mock.recipeVersionId.value} of recipe {retire_recipe_version_command_mock.recipeId.value} can't be found."
    )


def test_handle_should_raise_exception_when_version_name_is_invalid(
    get_retire_recipe_version_command_mock,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_name = "a.b.c"
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            version_name=recipe_version_name,
            status=recipe_version.RecipeVersionStatus.Released,
        )
    )
    retire_recipe_version_command_mock = get_retire_recipe_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_recipe_version_command_handler.handle(
            command=retire_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {recipe_version_name} is not a valid SemVer string."
    )


@pytest.mark.parametrize(
    "recipe_version_status",
    (
        recipe_version.RecipeVersionStatus.Created,
        recipe_version.RecipeVersionStatus.Creating,
        recipe_version.RecipeVersionStatus.Retired,
        recipe_version.RecipeVersionStatus.Testing,
        recipe_version.RecipeVersionStatus.Updating,
    ),
)
def test_handle_should_raise_exception_when_status_is_invalid(
    get_retire_recipe_version_command_mock,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    recipe_version_status,
    uow_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            version_name="1.0.0-rc.1",
            status=recipe_version_status,
        )
    )
    retire_recipe_version_command_mock = get_retire_recipe_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_recipe_version_command_handler.handle(
            command=retire_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {retire_recipe_version_command_mock.recipeVersionId.value} of recipe {retire_recipe_version_command_mock.recipeId.value} can't be retired while in {recipe_version_status} status."
    )


def test_handle_should_raise_exception_when_version_is_released_and_roles_are_not_allowed(
    get_retire_recipe_version_command_mock,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_name = "1.0.0"
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            version_name=recipe_version_name,
            status=recipe_version.RecipeVersionStatus.Released,
        )
    )
    retire_recipe_version_command_mock = get_retire_recipe_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_recipe_version_command_handler.handle(
            command=retire_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {recipe_version_name} of recipe {retire_recipe_version_command_mock.recipeId.value} has been released."
    )


@pytest.mark.parametrize(
    "recipe_version_name,recipe_version_status,user_roles",
    (
        (
            "1.0.0-rc.1",
            recipe_version.RecipeVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0-rc.1",
            recipe_version.RecipeVersionStatus.Validated,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.Admin,
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Released,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Released,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            recipe_version.RecipeVersionStatus.Released,
            [
                VirtualWorkbenchRoles.Admin,
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_retire_version(
    generic_repo_mock,
    get_retire_recipe_version_command_mock,
    get_test_recipe_name,
    get_test_recipe_version_arn,
    get_test_recipe_version_component_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    get_test_user_id,
    message_bus_mock,
    recipe_version_query_service_mock,
    recipe_version_name,
    recipe_version_status,
    uow_mock,
    user_roles,
):
    # ARRANGE
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name_and_status(
        version_name=recipe_version_name,
        status=recipe_version_status,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    retire_recipe_version_command_mock = get_retire_recipe_version_command_mock(user_roles=user_roles)

    # ACT
    retire_recipe_version_command_handler.handle(
        command=retire_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=retire_recipe_version_command_mock.recipeId.value,
            recipeVersionId=retire_recipe_version_command_mock.recipeVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=retire_recipe_version_command_mock.lastUpdatedBy.value,
        status=recipe_version.RecipeVersionStatus.Updating,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_retirement_started.RecipeVersionRetirementStarted(
            projectId=retire_recipe_version_command_mock.projectId.value,
            recipeId=retire_recipe_version_command_mock.recipeId.value,
            recipeName=get_test_recipe_name,
            recipeVersionId=retire_recipe_version_command_mock.recipeVersionId.value,
            recipeVersionArn=get_test_recipe_version_arn(version_name=recipe_version_name),
            recipeVersionComponentArn=get_test_recipe_version_component_arn(version_name=recipe_version_name),
            recipeVersionName=recipe_version_name,
            recipeComponentsVersions=recipe_version_entity.recipeComponentsVersions,
            lastUpdatedBy=get_test_user_id,
        )
    )
