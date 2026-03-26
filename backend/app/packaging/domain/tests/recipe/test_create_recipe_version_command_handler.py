import os
from unittest import mock

import boto3
import pytest
from assertpy import assertpy
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    create_recipe_version_command_handler,
)
from app.packaging.domain.events.recipe import recipe_version_creation_started
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_release_type_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        ("2.0.0", recipe_version.RecipeVersionReleaseType.Major.value, "3.0.0-rc.1"),
        ("2.0.100", recipe_version.RecipeVersionReleaseType.Major.value, "3.0.0-rc.1"),
        ("1.2.0", recipe_version.RecipeVersionReleaseType.Minor.value, "1.3.0-rc.1"),
        ("1.2.100", recipe_version.RecipeVersionReleaseType.Minor.value, "1.3.0-rc.1"),
        ("2.5.10", recipe_version.RecipeVersionReleaseType.Patch.value, "2.5.11-rc.1"),
    ),
)
@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_create_new_version_recipe_if_version_in_repository(
    fetched_release_name,
    release_type,
    expected_version_name,
    create_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeVersionReleaseType = recipe_version_release_type_value_object.from_str(
        release_type
    )
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    create_recipe_version_command_handler.handle(
        command=create_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        parameter_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    recipe_version_repo_mock.add.assert_called_once_with(
        recipe_version.RecipeVersion(
            recipeId="reci-1234abcd",
            recipeVersionId="vers-11111111",
            recipeVersionName=expected_version_name,
            recipeName="Test recipe",
            recipeVersionDescription="Test description",
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            status=recipe_version.RecipeVersionStatus.Creating,
            parentImageUpstreamId=get_test_ami_id,
            recipeVersionVolumeSize="8",
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id="proj-12345",
            recipe_id="reci-1234abcd",
            recipe_version_id="vers-11111111",
            recipe_version_description="Test description",
            recipe_version_name=expected_version_name,
            recipe_component_versions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            parent_image_upstream_id=get_test_ami_id,
            recipe_version_volume_size="8",
        )
    )


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        (None, recipe_version.RecipeVersionReleaseType.Major.value, "1.0.0-rc.1"),
        (None, recipe_version.RecipeVersionReleaseType.Minor.value, "1.0.0-rc.1"),
        (None, recipe_version.RecipeVersionReleaseType.Patch.value, "1.0.0-rc.1"),
    ),
)
@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_create_new_inital_version_for_recipe_if_no_version_in_repository(
    fetched_release_name,
    release_type,
    expected_version_name,
    create_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeVersionReleaseType = recipe_version_release_type_value_object.from_str(
        release_type
    )
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    create_recipe_version_command_handler.handle(
        command=create_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        parameter_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    recipe_version_repo_mock.add.assert_called_once_with(
        recipe_version.RecipeVersion(
            recipeId="reci-1234abcd",
            recipeVersionId="vers-11111111",
            recipeVersionName=expected_version_name,
            recipeName="Test recipe",
            recipeVersionDescription="Test description",
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            status=recipe_version.RecipeVersionStatus.Creating,
            parentImageUpstreamId=get_test_ami_id,
            recipeVersionVolumeSize="8",
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id="proj-12345",
            recipe_id="reci-1234abcd",
            recipe_version_id="vers-11111111",
            recipe_version_name=expected_version_name,
            recipe_version_description="Test description",
            recipe_component_versions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            status=recipe_version.RecipeVersionStatus.Creating,
            parent_image_upstream_id=get_test_ami_id,
            recipe_version_volume_size="8",
        )
    )


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        (None, recipe_version.RecipeVersionReleaseType.Major.value, "1.0.0-rc.1"),
        (None, recipe_version.RecipeVersionReleaseType.Minor.value, "1.0.0-rc.1"),
        (None, recipe_version.RecipeVersionReleaseType.Patch.value, "1.0.0-rc.1"),
    ),
)
@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_create_new_inital_version_for_recipe_if_no_version_in_repository_without_mandatory_components_component_version_type_set(
    fetched_release_name,
    release_type,
    expected_version_name,
    create_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions_without_component_version_type_set,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions_without_component_version_type_set()
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeVersionReleaseType = recipe_version_release_type_value_object.from_str(
        release_type
    )
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    create_recipe_version_command_handler.handle(
        command=create_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        parameter_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    recipe_version_repo_mock.add.assert_called_once_with(
        recipe_version.RecipeVersion(
            recipeId="reci-1234abcd",
            recipeVersionId="vers-11111111",
            recipeVersionName=expected_version_name,
            recipeName="Test recipe",
            recipeVersionDescription="Test description",
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            status=recipe_version.RecipeVersionStatus.Creating,
            parentImageUpstreamId=get_test_ami_id,
            recipeVersionVolumeSize="8",
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id="proj-12345",
            recipe_id="reci-1234abcd",
            recipe_version_id="vers-11111111",
            recipe_version_name=expected_version_name,
            recipe_version_description="Test description",
            recipe_component_versions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            status=recipe_version.RecipeVersionStatus.Creating,
            parent_image_upstream_id=get_test_ami_id,
            recipe_version_volume_size="8",
        )
    )


@pytest.mark.parametrize(
    "mandatory_components_versions,recipe_component_versions,expected_recipe_component_versions",
    (
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
            ],
        ),
    ),
)
@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_create_new_version_recipe_with_correct_component_versions(
    mandatory_components_versions,
    recipe_component_versions,
    expected_recipe_component_versions,
    create_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions(
            mandatory_components_versions=mandatory_components_versions
        )
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeComponentsVersions = (
        recipe_version_components_versions_value_object.from_list(recipe_component_versions)
    )
    create_recipe_version_command_mock.recipeVersionReleaseType = recipe_version_release_type_value_object.from_str(
        recipe_version.RecipeVersionReleaseType.Major.value
    )
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    create_recipe_version_command_handler.handle(
        command=create_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        parameter_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    recipe_version_repo_mock.add.assert_called_once_with(
        recipe_version.RecipeVersion(
            recipeId="reci-1234abcd",
            recipeVersionId="vers-11111111",
            recipeVersionName="2.0.0-rc.1",
            recipeName="Test recipe",
            recipeVersionDescription="Test description",
            recipeComponentsVersions=expected_recipe_component_versions,
            status=recipe_version.RecipeVersionStatus.Creating,
            parentImageUpstreamId=get_test_ami_id,
            recipeVersionVolumeSize="8",
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id="proj-12345",
            recipe_id="reci-1234abcd",
            recipe_version_id="vers-11111111",
            recipe_version_description="Test description",
            recipe_version_name="2.0.0-rc.1",
            recipe_component_versions=expected_recipe_component_versions,
            parent_image_upstream_id=get_test_ami_id,
            recipe_version_volume_size="8",
        )
    )


def test_handle_should_raise_exception_if_recipe_not_found(
    create_recipe_version_command_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    recipe_query_service_mock.get_recipe.return_value = None
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe {create_recipe_version_command_mock.recipeId.value} can not be found."
    )


def test_handle_should_raise_exception_if_recipe_status_is_archived(
    create_recipe_version_command_mock,
    mock_recipe_object,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    test_recipe = mock_recipe_object
    test_recipe.status = recipe.RecipeStatus.Archived
    recipe_query_service_mock.get_recipe.return_value = test_recipe
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe {create_recipe_version_command_mock.recipeId.value} is in ARCHIVED status."
    )


@pytest.mark.parametrize(
    "fetched_release_name,release_type",
    (
        (None, recipe_version.RecipeVersionReleaseType.Major.value),
        (None, recipe_version.RecipeVersionReleaseType.Minor.value),
        (None, recipe_version.RecipeVersionReleaseType.Patch.value),
    ),
)
@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
def test_handle_should_raise_exception_if_parameter_doesnt_exist_when_creating_new_version(
    fetched_release_name,
    release_type,
    create_recipe_version_command_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
):
    # ARRANGE
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeVersionReleaseType = recipe_version_release_type_value_object.from_str(
        release_type
    )
    parameter_service_mock.get_parameter_value.side_effect = boto3.client(
        "ssm", region_name="us-east-1"
    ).exceptions.ParameterNotFound(
        operation_name="GetParameter",
        error_response={"Code": "ParameterNotFound", "Message": ""},
    )

    # ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Parameter ami_ssm_param_name not found.")


def test_handle_should_raise_an_exception_if_recipe_component_versions_don_t_exist(
    create_recipe_version_command_mock,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    component_version_query_service_mock.get_component_version.side_effect = [
        None for _ in range(len(create_recipe_version_command_mock.recipeComponentsVersions.value))
    ]
    first_recipe_component_version = create_recipe_version_command_mock.recipeComponentsVersions.value[0]

    # ACT
    with pytest.raises(DomainException) as e:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {first_recipe_component_version.componentVersionId} of component "
        f"{first_recipe_component_version.componentId} does not exist."
    )


@pytest.mark.parametrize(
    "status",
    (
        component_version.ComponentVersionStatus.Created,
        component_version.ComponentVersionStatus.Creating,
        component_version.ComponentVersionStatus.Failed,
        component_version.ComponentVersionStatus.Retired,
        component_version.ComponentVersionStatus.Testing,
        component_version.ComponentVersionStatus.Updating,
    ),
)
def test_handle_should_raise_an_exception_if_recipe_component_versions_are_not_validated_or_released(
    create_recipe_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    status,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_version_name_and_status(
            version_name=recipe_component_version.componentVersionName,
            status=status,
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities
    first_recipe_component_version = create_recipe_version_command_mock.recipeComponentsVersions.value[0]

    # ACT
    with pytest.raises(DomainException) as e:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {first_recipe_component_version.componentVersionName} of component "
        f"{first_recipe_component_version.componentId} can't be included in this recipe version "
        f"while in {status} status: only {component_version.ComponentVersionStatus.Released} "
        f"and {component_version.ComponentVersionStatus.Validated} states are accepted."
    )


@pytest.mark.parametrize(
    "mandatory_components_versions,recipe_component_versions,expected_exception_message",
    (
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            "Recipe version contains duplicate components: ['component-1234abc']. Components ['component-1234abc'] are prepended automatically and shouldn't be re-included.",
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
            "Recipe version contains duplicate components: ['component-1234def'].",
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
            ],
            "Recipe version contains duplicate components: ['component-1234abc', 'component-1234def']. Components ['component-1234abc'] are prepended automatically and shouldn't be re-included.",
        ),
    ),
)
def test_handle_should_raise_exception_with_duplicate_components(
    mandatory_components_versions,
    recipe_component_versions,
    expected_exception_message,
    create_recipe_version_command_mock,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions(
            mandatory_components_versions=mandatory_components_versions
        )
    )
    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_recipe_version_command_mock.recipeComponentsVersions = (
        recipe_version_components_versions_value_object.from_list(recipe_component_versions)
    )
    component_version_entities = list()
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    with pytest.raises(DomainException) as e:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_order_components_prepended_user_appended(
    create_recipe_version_command_mock,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_positioned_components,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}

    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_positioned_components()
    )

    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    component_version_entities = []
    for recipe_component_version in create_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId
        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    create_recipe_version_command_handler.handle(
        command=create_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        parameter_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    call_args = recipe_version_repo_mock.add.call_args[0][0]
    components = call_args.recipeComponentsVersions

    # Verify correct number of components and their order
    assertpy.assert_that(components).is_length(6)  # 2 prepended + 3 user + 1 appended
    # Verify components are in correct order (prepended first, then user, then appended)
    for idx, comp in enumerate(components, start=1):
        assertpy.assert_that(comp.order).is_equal_to(idx)


@mock.patch("app.packaging.domain.model.recipe.recipe_version.random.choice", lambda _: "1")
@freeze_time("2023-09-29")
def test_handle_should_detect_duplicate_mandatory_components(
    create_recipe_version_command_with_duplicate_mandatory_component,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_positioned_components,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mock_system_configuration_mapping,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}

    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_positioned_components()
    )

    recipe_version_query_service_mock.get_latest_recipe_version_name.return_value = "1.0.0"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    component_version_entities = []
    for (
        recipe_component_version
    ) in create_recipe_version_command_with_duplicate_mandatory_component.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId
        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT & ASSERT
    with pytest.raises(DomainException) as exc_info:
        create_recipe_version_command_handler.handle(
            command=create_recipe_version_command_with_duplicate_mandatory_component,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            parameter_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    assertpy.assert_that(str(exc_info.value)).contains("duplicate components")
