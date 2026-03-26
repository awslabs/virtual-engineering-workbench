from unittest import mock

import pytest
from assertpy import assertpy
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    create_automated_recipe_version_command_handler,
)
from app.packaging.domain.commands.recipe import create_automated_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_creation_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_release_type_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def _create_default_recipe_mock():
    """Helper to create a default recipe mock for tests."""
    recipe_mock = mock.Mock()
    recipe_mock.recipePlatform = "AL2023"
    recipe_mock.recipeOsVersion = "2023"
    recipe_mock.recipeArchitecture = "x86_64"
    return recipe_mock


@freeze_time("2023-09-29")
def test_handle_should_create_new_recipe_version_with_updated_component():
    # ARRANGE
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("PATCH"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    # Mock recipe entity
    recipe_mock = mock.Mock()
    recipe_mock.recipePlatform = "AL2023"
    recipe_mock.recipeOsVersion = "2023"
    recipe_mock.recipeArchitecture = "x86_64"
    recipe_query_service_mock.get_recipe.return_value = recipe_mock

    # Mock mandatory components (none for this test)
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.0.0",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[
            ComponentVersionEntry(
                componentId="component-12345",
                componentVersionId="old-comp-version-12345",
                order=1,
                componentName="Test Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
            ComponentVersionEntry(
                componentId="other-component-12345",
                componentVersionId="other-comp-version-12345",
                order=2,
                componentName="Other Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
        ],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"

    component_version_mock = mock.Mock()
    component_version_mock.componentVersionName = "1.0.1"
    component_version_query_service_mock.get_component_version.return_value = component_version_mock

    # ACT
    result = create_automated_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_query_service=component_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result).is_not_none()

    recipe_version_repo_mock.add.assert_called_once()

    added_recipe_version = recipe_version_repo_mock.add.call_args[0][0]
    assertpy.assert_that(result).is_equal_to(added_recipe_version.recipeVersionId)

    assertpy.assert_that(added_recipe_version.recipeId).is_equal_to("recipe-12345")
    assertpy.assert_that(added_recipe_version.recipeVersionName).is_equal_to("1.0.1-rc.1")
    assertpy.assert_that(added_recipe_version.status).is_equal_to(recipe_version.RecipeVersionStatus.Creating)

    component_entries = added_recipe_version.recipeComponentsVersions
    assertpy.assert_that(component_entries).is_length(2)

    updated_component = next((c for c in component_entries if c.componentId == "component-12345"), None)
    assertpy.assert_that(updated_component).is_not_none()
    assertpy.assert_that(updated_component.componentVersionId).is_equal_to("comp-version-12345")
    assertpy.assert_that(updated_component.componentVersionName).is_equal_to("1.0.1")

    uow_mock.commit.assert_called_once()

    message_bus_mock.publish.assert_called_once()
    published_event = message_bus_mock.publish.call_args[0][0]
    assertpy.assert_that(published_event).is_instance_of(recipe_version_creation_started.RecipeVersionCreationStarted)
    assertpy.assert_that(published_event.recipe_id).is_equal_to("recipe-12345")
    assertpy.assert_that(published_event.recipe_version_name).is_equal_to("1.0.1-rc.1")
    assertpy.assert_that(published_event.recipe_component_versions).is_length(2)
    event_updated_component = next(
        (c for c in published_event.recipe_component_versions if c.componentId == "component-12345"),
        None,
    )
    assertpy.assert_that(event_updated_component).is_not_none()
    assertpy.assert_that(event_updated_component.componentVersionId).is_equal_to("comp-version-12345")


@freeze_time("2023-09-29")
def test_handle_should_create_new_recipe_version_with_new_component():
    # ARRANGE
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # Mock recipe and mandatory components
    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("new-component-12345"),
        componentVersionId=component_version_id_value_object.from_str("new-comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("PATCH"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.0.0",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[
            ComponentVersionEntry(
                componentId="component-12345",
                componentVersionId="comp-version-12345",
                order=1,
                componentName="Test Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
        ],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"

    component_mock = mock.Mock()
    component_mock.componentName = "New Component"
    component_query_service_mock.get_component.return_value = component_mock

    component_version_mock = mock.Mock()
    component_version_mock.componentVersionName = "1.0.0"
    component_version_query_service_mock.get_component_version.return_value = component_version_mock

    # ACT
    result = create_automated_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_query_service=component_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    recipe_version_repo_mock.add.assert_called_once()

    added_recipe_version = recipe_version_repo_mock.add.call_args[0][0]

    assertpy.assert_that(added_recipe_version.recipeId).is_equal_to("recipe-12345")
    assertpy.assert_that(added_recipe_version.recipeVersionName).is_equal_to("1.0.1-rc.1")
    assertpy.assert_that(added_recipe_version.status).is_equal_to(recipe_version.RecipeVersionStatus.Creating)

    component_entries = added_recipe_version.recipeComponentsVersions
    assertpy.assert_that(component_entries).is_length(2)

    new_component = next((c for c in component_entries if c.componentId == "new-component-12345"), None)
    assertpy.assert_that(new_component).is_not_none()
    assertpy.assert_that(new_component.componentVersionId).is_equal_to("new-comp-version-12345")
    assertpy.assert_that(new_component.componentName).is_equal_to("New Component")
    assertpy.assert_that(new_component.componentVersionName).is_equal_to("1.0.0")
    assertpy.assert_that(new_component.componentVersionType).is_equal_to("MAIN")

    uow_mock.commit.assert_called_once()

    message_bus_mock.publish.assert_called_once()
    published_event = message_bus_mock.publish.call_args[0][0]
    assertpy.assert_that(published_event).is_instance_of(recipe_version_creation_started.RecipeVersionCreationStarted)


@freeze_time("2023-09-29")
def test_handle_should_raise_exception_when_no_released_recipe_version_found():
    # ARRANGE
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MAJOR"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    recipe_version_mock = mock.Mock()
    recipe_version_mock.status = recipe_version.RecipeVersionStatus.Creating
    recipe_versions = [recipe_version_mock]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as excinfo:
        create_automated_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            component_query_service=component_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            recipe_query_service=recipe_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    assertpy.assert_that(str(excinfo.value)).contains("No released recipe version found")


@freeze_time("2023-09-29")
def test_handle_should_raise_exception_when_component_not_found():
    # ARRANGE
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("new-component-12345"),
        componentVersionId=component_version_id_value_object.from_str("new-comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MAJOR"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.0.0",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"

    component_query_service_mock.get_component.return_value = None
    component_version_query_service_mock.get_component_version.return_value = None

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as excinfo:
        create_automated_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            component_query_service=component_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            recipe_query_service=recipe_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    assertpy.assert_that(str(excinfo.value)).contains("Component").contains("or version").contains("not found")


@freeze_time("2023-09-29")
def test_handle_should_raise_exception_when_invalid_semver():
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MAJOR"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = mock.Mock()
    last_released_version.status = recipe_version.RecipeVersionStatus.Released
    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions

    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "invalid-semver"

    with pytest.raises(domain_exception.DomainException) as excinfo:
        create_automated_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            component_query_service=component_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            recipe_query_service=recipe_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    assertpy.assert_that(str(excinfo.value)).contains("not a valid SemVer string")


@freeze_time("2023-09-29")
def test_handle_should_calculate_major_version_correctly():
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MAJOR"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.2.3",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[
            ComponentVersionEntry(
                componentId="component-12345",
                componentVersionId="old-comp-version-12345",
                order=1,
                componentName="Test Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
        ],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.2.3"

    component_version_mock = mock.Mock()
    component_version_mock.componentVersionName = "1.0.1"
    component_version_query_service_mock.get_component_version.return_value = component_version_mock

    result = create_automated_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_query_service=component_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    assertpy.assert_that(result).is_not_none()
    added_recipe_version = recipe_version_repo_mock.add.call_args[0][0]
    assertpy.assert_that(added_recipe_version.recipeVersionName).is_equal_to("2.0.0-rc.1")


@freeze_time("2023-09-29")
def test_handle_should_calculate_minor_version_correctly():
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("MINOR"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.2.3",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[
            ComponentVersionEntry(
                componentId="component-12345",
                componentVersionId="old-comp-version-12345",
                order=1,
                componentName="Test Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
        ],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.2.3"

    component_version_mock = mock.Mock()
    component_version_mock.componentVersionName = "1.0.1"
    component_version_query_service_mock.get_component_version.return_value = component_version_mock

    result = create_automated_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_query_service=component_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    assertpy.assert_that(result).is_not_none()
    added_recipe_version = recipe_version_repo_mock.add.call_args[0][0]
    assertpy.assert_that(added_recipe_version.recipeVersionName).is_equal_to("1.3.0-rc.1")


@freeze_time("2023-09-29")
def test_handle_should_create_initial_version_when_no_previous_version():
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    recipe_query_service_mock.get_recipe.return_value = _create_default_recipe_mock()
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("PATCH"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    last_released_version = recipe_version.RecipeVersion(
        recipeId="recipe-12345",
        recipeVersionId="old-version-12345",
        recipeVersionName="1.0.0",
        recipeName="Test Recipe",
        recipeVersionDescription="Test Description",
        recipeComponentsVersions=[
            ComponentVersionEntry(
                componentId="component-12345",
                componentVersionId="old-comp-version-12345",
                order=1,
                componentName="Test Component",
                componentVersionName="1.0.0",
                componentVersionType="MAIN",
            ),
        ],
        status=recipe_version.RecipeVersionStatus.Released,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        recipeVersionIntegrations=[],
        createDate="2023-09-28T00:00:00+00:00",
        createdBy="user-12345",
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="user-12345",
    )

    recipe_versions = [last_released_version]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = None

    component_version_mock = mock.Mock()
    component_version_mock.componentVersionName = "1.0.1"
    component_version_query_service_mock.get_component_version.return_value = component_version_mock

    result = create_automated_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_query_service=component_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    assertpy.assert_that(result).is_not_none()
    added_recipe_version = recipe_version_repo_mock.add.call_args[0][0]
    assertpy.assert_that(added_recipe_version.recipeVersionName).is_equal_to("1.0.0-rc.1")


@freeze_time("2023-09-29")
def test_handle_should_raise_exception_when_recipe_not_found():
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_query_service_mock = mock.Mock()
    recipe_query_service_mock = mock.Mock()
    component_query_service_mock = mock.Mock()
    component_version_query_service_mock = mock.Mock()
    mandatory_components_list_query_service_mock = mock.Mock()

    recipe_query_service_mock.get_recipe.return_value = None

    command = create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        componentId=component_id_value_object.from_str("component-12345"),
        componentVersionId=component_version_id_value_object.from_str("comp-version-12345"),
        projectId=project_id_value_object.from_str("project-12345"),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str("PATCH"),
        createdBy=user_id_value_object.from_str("user-12345"),
    )

    with pytest.raises(domain_exception.DomainException) as excinfo:
        create_automated_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_query_service=recipe_query_service_mock,
            component_query_service=component_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    assertpy.assert_that(str(excinfo.value)).contains("Recipe").contains("not found")
